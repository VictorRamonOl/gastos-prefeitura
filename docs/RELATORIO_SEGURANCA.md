# Relatório de Segurança — Portal Maués

Status pós-auditoria (2026-05-28).

---

## ✅ Implementado nesta auditoria

### Rede / Firewall
- Containers Docker (portal, gastos, bb_arrecadacao) agora bindam **apenas `127.0.0.1`**. Portas `8500/8501/8502/8082` **não respondem mais externamente**.
- UFW: 22/80/443 abertas; 3306 só pra `172.0.0.0/8` (network interna Docker).
- nginx com `default_server` que retorna `444` (drop) pra qualquer requisição com `Host` desconhecido — bloqueia scanners que batem direto no IP sem hostname.

### Nginx — hardening
- Headers de segurança: `X-Frame-Options DENY`, `X-Content-Type-Options nosniff`, `X-XSS-Protection`, `Referrer-Policy strict-origin-when-cross-origin`, `Permissions-Policy`, `Content-Security-Policy`.
- Bloqueio de bots conhecidos (nikto/sqlmap/nmap/etc).
- Bloqueio de paths sensíveis (`.env`, `.git`, `wp-admin`, `phpmyadmin`, etc).
- Bloqueio de requisições sem User-Agent.
- Rate limit: **60 req/min** por IP (`portal_general`), com burst 20. Zonas extras preparadas pra `portal_login` (5/min) e `portal_export` (10/min).
- `server_tokens off` (esconde versão).

### SSH
- Chave pública ed25519 instalada em `/root/.ssh/authorized_keys` (chave privada em `~/.ssh/portal_maues_vps` no PC do Victor).
- `MaxAuthTries 3`, `X11Forwarding no`, `ClientAliveInterval 300`, `ClientAliveCountMax 2`.
- **Pendente**: desabilitar `PasswordAuthentication` e `PermitRootLogin yes`. Adiada porque a chave Windows ainda tem bug de permissão NTFS — precisa validar antes de cortar acesso por senha. Ver TODO no fim.

### MySQL
- `root@localhost` usa `auth_socket` (autenticação por socket Unix, sem senha de rede).
- Usuário de aplicação `portal_app` com privilégios apenas em `gastos_prefeitura.*`, acesso de `localhost` e `172.%`.
- Senha do `portal_app` em `/root/.portal_db_pass` (chmod 600) e injetada via `.env` no container.
- Bind em `0.0.0.0` mas firewalled (UFW + Docker network).

### Backup
- Cron diário às 04h: `/usr/local/bin/backup-portal.sh`.
- Dump `gzip` em `/opt/backup/gastos_YYYY-MM-DD_HHMM.sql.gz`.
- Retenção 30 dias.
- Log em `/var/log/portal-backup.log`.

### fail2ban
- 5 jails ativos: `sshd`, `nginx-http-auth`, `nginx-botsearch`, `nginx-noscript`, `nginx-noproxy`.
- Ban automático: 5 falhas em 10min → 1h banido (sshd) / 2-3 falhas → 1h (nginx).

### Sistema
- Pacotes apt atualizados.
- `unattended-upgrades` (já vinha ativo na Hostinger).

### Aplicação
- Login obrigatório em **todas as páginas** via `verificar_login`/`login_requerido`.
- 4 perfis no `usuarios.json` (admin, gestor, secretario, visualizador) — base pra ACL futura.
- Permissões por dashboard (`utils/permissoes.py`).
- Senhas armazenadas com bcrypt (custo 12).
- SQL Injection: todas as queries da aplicação usam `cursor.execute(sql, params)` parametrizado — verificado em `app/db.py` e ETL.
- Exportações Excel/CSV: arquivos gerados em memória (BytesIO), sem escrita em filesystem (sem path traversal).

---

## 🟡 Riscos remanescentes (TODO)

| Risco                                                        | Mitigação proposta                                                            | Prioridade |
|--------------------------------------------------------------|-------------------------------------------------------------------------------|------------|
| Sem HTTPS — login/senha viajam em texto puro                 | Comprar domínio (`prefeituramaues.com.br` ou similar) + colocar Cloudflare na frente (HTTPS grátis, WAF, hide IP) | 🔴 alta    |
| Sem MFA                                                       | Adicionar TOTP no `auth_central.py` ou usar Cloudflare Access com Google OAuth | 🟡 média   |
| Sem log de auditoria em código                                | Tabela `auditoria` (user, ip, ts, ação) + decorator nas views sensíveis        | 🟡 média   |
| Permissão por secretaria não implementada                    | Filtrar `pagamentos` por `secretaria` quando perfil = `secretario`            | 🟡 média   |
| `PasswordAuthentication yes` no SSH                          | Validar chave funcionando → desabilitar senha SSH                              | 🟡 média   |
| MySQL bind em `0.0.0.0`                                      | Mudar pra `172.17.0.1` ou usar docker network compartilhada                   | 🟢 baixa   |
| Sem isolamento de container (root no container)              | Adicionar `user: 1000:1000` no docker-compose                                  | 🟢 baixa   |
| Sem teste de restore do backup                                | Cron mensal que restaura em DB temporário e valida count(*)                   | 🟢 baixa   |

---

## Como acessar agora

| Recurso              | URL / Caminho                                  | Observação                                |
|----------------------|------------------------------------------------|--------------------------------------------|
| Portal               | http://187.127.10.188                          | Login `victor` / senha definida no usuarios.json |
| SSH                  | `ssh root@187.127.10.188`                      | Senha conhecida + chave instalada (não desabilitar senha ainda) |
| Backup do banco      | `/opt/backup/gastos_*.sql.gz` no VPS           | Daily 04h, retenção 30d                    |
| Logs nginx           | `/var/log/nginx/{access,error}.log`            | Usado pelo fail2ban                        |
| Logs fail2ban        | `journalctl -u fail2ban -f`                    |                                           |
| Status containers    | `docker ps`                                     |                                           |

---

## Checklist final antes de liberar pra prefeita

- [x] Login obrigatório
- [x] Portas internas fechadas externamente
- [x] Headers de segurança ativos
- [x] Rate limit configurado
- [x] fail2ban com 5 jails
- [x] Backup automático rodando
- [x] SQL parametrizado (sem injection)
- [x] Bloqueio de bots e paths sensíveis
- [x] Pacotes atualizados
- [ ] **HTTPS via Cloudflare + domínio** ← bloqueador pra liberar pra externos
- [ ] **MFA pra usuários** ← bloqueador pra acesso da prefeita
- [ ] **Permissões por secretaria** ← bloqueador pra acesso de secretários
- [ ] Log de auditoria de ações
- [ ] SSH só com chave

### Recomendação executiva
**Sistema seguro o suficiente** pra acesso interno e demonstração. **Não deve ainda ser passado** pra usuários externos (prefeita, secretários) **sem antes** ter:
1. Domínio + HTTPS via Cloudflare (sem isso, login/senha é interceptável).
2. MFA ou Cloudflare Access (sem isso, comprometer um e-mail = comprometer o sistema).
3. Permissões por secretaria (sem isso, secretário de Saúde veria dados de Educação).

Tempo estimado pra fechar esses 3 itens: **8-12h de trabalho** após você ter o domínio em mãos.

---

## Comandos úteis pra rotina

```bash
# Ver últimos bans do fail2ban
fail2ban-client status sshd
fail2ban-client status nginx-botsearch

# Desbanir um IP que entrou por engano
fail2ban-client set sshd unbanip 1.2.3.4

# Ver últimos backups
ls -lh /opt/backup/

# Rodar backup manual
/usr/local/bin/backup-portal.sh

# Restaurar último backup
zcat /opt/backup/gastos_2026-05-28_0451.sql.gz | mysql -uroot

# Ver headers de segurança em produção
curl -sI http://187.127.10.188/ | grep -E '^(X-|Content-Security|Referrer|Permissions)'

# Logs do nginx em tempo real
tail -f /var/log/nginx/access.log

# Status geral
docker ps && ufw status && systemctl is-active fail2ban nginx mysql
```
