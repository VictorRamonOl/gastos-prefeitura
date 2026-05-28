# Arquitetura — Sincronização automática via Google Drive

> Status: **planejamento**. Não está implementado ainda. Documento serve para alinhar
> a próxima fase do sistema quando o template padrão (`MODELO_DESPESAS_PREFEITURA.xlsx`)
> estiver em uso.

---

## Visão geral do fluxo proposto

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Prefeitura     │    │  Google Drive    │    │  VPS Hostinger  │
│  (operadora)    │    │  (pasta única)   │    │  187.127.10.188 │
└────────┬────────┘    └────────┬─────────┘    └────────┬────────┘
         │                      │                       │
         │ 1. Atualiza Excel    │                       │
         │ na sua máquina       │                       │
         │                      │                       │
         │ 2. Sobe na pasta     │                       │
         │ compartilhada ───────►                       │
         │                      │                       │
         │                      │ 3. A cada 6h o VPS    │
         │                      │ pergunta ao Drive:    │
         │                      │ "tem arquivo novo?"   │
         │                      │ ◄─────────────────────┤
         │                      │                       │
         │                      │ 4. Se mudou hash →    │
         │                      │ baixa o .xlsx ────────►
         │                      │                       │
         │                      │ 5. Roda etl/run_etl.py│
         │                      │ Banco atualizado.     │
         │                      │                       │
         │                      │ 6. Notifica operadora │
         │                      │ por e-mail (ok/erro)  │
```

## 1. Componentes

### 1.1 Pasta no Google Drive
- **Nome sugerido:** `Prefeitura Maués — Despesas (Sistema)`
- **Estrutura:**
  ```
  Prefeitura Maués — Despesas (Sistema)/
  ├── MODELO_DESPESAS_PREFEITURA.xlsx       ← template em branco (referência)
  ├── 2026/
  │   └── DESPESAS_2026.xlsx                ← arquivo do ano corrente
  ├── 2025/
  │   └── DESPESAS_2025.xlsx                ← histórico
  └── _logs/
      └── import_YYYY-MM-DD.log             ← gerado pelo VPS
  ```
- Compartilhada com o e-mail de uma **Service Account** do Google Cloud (não com
  conta pessoal — evita problemas se o operador trocar).

### 1.2 Service Account (Google Cloud)
- Conta de serviço criada em https://console.cloud.google.com → IAM & Admin → Service Accounts
- Permissão: **só leitura** na pasta compartilhada.
- Chave JSON baixada e salva no VPS em `/root/.gdrive/service-account.json` (chmod 600).
- A chave **nunca** entra no git. Adicionar `*.json` em `.gitignore` da pasta `etl/`.

### 1.3 Watcher no VPS
Novo script: `etl/watch_drive.py`

Responsabilidades:
1. Conecta ao Drive via `google-api-python-client` usando a Service Account.
2. Lista arquivos `.xlsx` na pasta monitorada com seus `modifiedTime` e `md5Checksum`.
3. Compara com a tabela `arquivos_importados` do MySQL (campo novo `gdrive_file_id` e `gdrive_md5`).
4. Se houver mudança:
   - Baixa pra `data/uploads/`.
   - Chama `etl.run_etl.processar_arquivo()`.
   - Registra resultado no banco e em `_logs/import_YYYY-MM-DD.log` (escreve de volta no Drive).
   - Envia e-mail pra operadora com o resumo (linhas inseridas, duplicadas, erros).

### 1.4 Agendamento
Cron no VPS:
```
0 6,18 * * * /usr/bin/python3 /opt/portal-maueis/gastos-prefeitura/etl/watch_drive.py >> /var/log/portal-watch.log 2>&1
```
Roda às 06h e 18h. Duas verificações por dia bastam — o operador tipicamente
atualiza a planilha 1× ao final do dia.

---

## 2. Detecção de mudança e prevenção de duplicidade

O sistema **já tem** a base pronta:
- Cada linha tem `hash_linha` (SHA-256) único.
- Cada arquivo tem `hash_arquivo` armazenado em `arquivos_importados`.
- O ETL atual (`etl/load.py::_chave_arquivo`) normaliza variações do nome (ex: `2026..xlsx`).

Adicionar no watcher:
- Campo `gdrive_md5` na tabela `arquivos_importados`.
- Antes de baixar: comparar `md5Checksum` do Drive com `gdrive_md5` no banco.
  Igual ⇒ pula. Diferente ⇒ baixa e reimporta.
- Antes de inserir: ETL atual já desduplica por `hash_linha` (INSERT IGNORE).

## 3. Validação antes de importar

`etl/validator.py` (novo módulo):

Antes de chamar `carregar()`, valida:

| Regra                               | Erro se…                                                 |
|-------------------------------------|----------------------------------------------------------|
| Estrutura do arquivo                | Faltam abas `Lançamentos` ou `Fornecedores`              |
| Cabeçalhos da aba Lançamentos       | Algum nome de coluna esperado está ausente               |
| Datas                               | `Data` fora do intervalo 2020–2050 ou nula em > 5% das linhas |
| Valores                             | `Valor` nulo, zero ou negativo em > 1% das linhas        |
| Fornecedor sem cadastro             | Há linha em `Lançamentos` com fornecedor que não existe na aba `Fornecedores` |
| Secretaria fora do catálogo         | Algum valor de `Secretaria` não está em `Catálogo_Secretarias` |
| Recurso fora do catálogo            | Idem para Recurso                                        |
| CNPJ malformado (quando presente)   | Não bate regex `\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}`         |

Erro grave (estrutura/cabeçalhos) ⇒ rejeita o arquivo, não importa nada, e-mail vermelho.
Erro leve (valores fora do catálogo) ⇒ importa o resto, e-mail amarelo com lista das linhas problemáticas.

## 4. Logs

Tabela nova: `logs_importacao`
```sql
CREATE TABLE logs_importacao (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  iniciado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finalizado_em DATETIME,
  fonte         ENUM('manual','gdrive') NOT NULL,
  arquivo_nome  VARCHAR(200),
  gdrive_md5    VARCHAR(32),
  linhas_lidas  INT,
  linhas_ins    INT,
  linhas_dup    INT,
  linhas_erro   INT,
  validacao     JSON,                -- avisos do validator
  status        ENUM('ok','parcial','erro') NOT NULL,
  mensagem      TEXT
);
```

Visível na aba **Admin** do dashboard com filtro por data/status.

## 5. Notificação por e-mail

Usar `smtplib` direto com SMTP do Gmail (App Password) ou SendGrid.
- **Verde**: importação OK, X lançamentos novos. (1 linha)
- **Amarelo**: importação parcial, ver detalhes anexos. (lista de avisos)
- **Vermelho**: arquivo rejeitado. (erro estrutural, ação necessária)

## 6. Segurança

| Risco                            | Mitigação                                                            |
|----------------------------------|-----------------------------------------------------------------------|
| Vazamento da chave Service Acct  | `chmod 600`, fora do git, rotação anual                              |
| Arquivo corrompido derruba ETL   | Try/except em cada etapa, transação SQL desfeita em erro            |
| Sobrescrita de dados bons        | Backup automático do dump SQL antes de cada importação              |
| Operador apaga o Excel no Drive  | Versionamento nativo do Drive (30 dias) + dump diário no VPS         |
| Ataque por arquivo malicioso     | Validar MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` antes de abrir |

### Backup automático
```
0 5 * * * /usr/bin/mysqldump gastos_prefeitura | gzip > /opt/backup/gastos_$(date +\%F).sql.gz
0 5 * * 0 find /opt/backup -name '*.sql.gz' -mtime +30 -delete
```
Diário com retenção de 30 dias.

## 7. Estimativa de esforço

| Etapa                                  | Esforço | Pré-requisito                |
|----------------------------------------|---------|------------------------------|
| Service Account + permissões no Drive  | 30 min  | Conta Google Cloud           |
| `etl/watch_drive.py` base              | 2-3 h   | Template em uso há ≥1 mês    |
| Tabela `logs_importacao` + admin view  | 1-2 h   | -                            |
| Validator                              | 2-3 h   | Template estável             |
| E-mail notificações                    | 1 h     | App Password ou SendGrid     |
| Cron + backup automático               | 30 min  | -                            |
| **Total**                              | **7-10 h** |                            |

## 8. Roadmap sugerido

1. **Agora**: prefeitura começa a usar o template (`MODELO_DESPESAS_PREFEITURA.xlsx`).
2. **Em 2-4 semanas**: ajustar catálogos do template conforme uso real (novas secretarias, novos recursos).
3. **Quando o template estiver estável**: implementar o watcher (item 1.3) e a Service Account.
4. **Após watcher rodando bem**: adicionar validator (item 3) e notificação por e-mail (item 5).
5. **Maturidade**: dashboard tem painel "Última importação" mostrando status do watcher em tempo real.

---

**Observação prática:** todo esse fluxo só faz sentido quando o template estiver
em uso consistente. Se a prefeitura continuar enviando arquivos com formato
livre, o watcher vai rejeitar tudo — gasto desnecessário. Priorize **adoção do template** primeiro.
