# Gastos Prefeitura — Dashboard de Despesas

Projeto de análise e visualização de despesas municipais.

## Arquitetura

```
Excel (planilhas) → ETL Python → MySQL → Streamlit Dashboard → usuário com login
```

## Estrutura

```
gastos-prefeitura/
├── app/
│   ├── app.py          # Dashboard Streamlit (ponto de entrada)
│   ├── auth.py         # Autenticação (login/logout/bcrypt)
│   └── db.py           # Conexão MySQL
├── etl/
│   ├── extract.py      # Leitura dos arquivos Excel
│   ├── transform.py    # Limpeza e normalização dos dados
│   ├── load.py         # Carga no MySQL (com deduplicação)
│   └── run_etl.py      # Ponto de entrada do ETL
├── sql/
│   └── schema.sql      # Criação das tabelas
├── scripts/
│   └── criar_admin.py  # Cria/atualiza usuários
├── data/
│   └── uploads/        # Arquivos Excel (não commitados)
├── .env                # Credenciais (NÃO commitar)
├── .env.example        # Modelo do .env
├── .gitignore
└── requirements.txt
```

## Configuração inicial

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar o banco de dados

Copie `.env.example` para `.env` e preencha com suas credenciais:

```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=gastos_prefeitura
DB_USER=root
DB_PASSWORD=sua_senha
```

### 3. Criar as tabelas no MySQL

```bash
mysql -u root -p < sql/schema.sql
```

### 4. Colocar os arquivos Excel

Copie as planilhas para a pasta `data/uploads/`:

```
data/uploads/PLANILHA DE DESPESAS PAGAS 2025.xlsx
data/uploads/PLANILHA DE DESPESAS PAGAS 2026..xlsx
```

### 5. Rodar o ETL

```bash
python etl/run_etl.py
```

Para processar arquivos específicos:

```bash
python etl/run_etl.py data/uploads/PLANILHA2025.xlsx
```

### 6. Criar o primeiro usuário admin

```bash
python scripts/criar_admin.py
```

### 7. Rodar o dashboard

```bash
streamlit run app/app.py
```

## Controle de acesso

- Perfil **admin**: acessa o dashboard + painel de logs de importação e lista de usuários
- Perfil **viewer**: acessa apenas o dashboard
- Senhas são armazenadas com hash bcrypt (nunca em texto puro)

## Adicionar novos usuários

```bash
# Interativo
python scripts/criar_admin.py

# Com argumentos
python scripts/criar_admin.py walter senha123 "Walter Silva" viewer
```

## Hospedagem

Para hospedar em servidor/cloud, os passos são:

1. Subir o código para o GitHub (sem `.env` e sem os Excel)
2. No servidor: clonar o repo, criar `.env` com as credenciais do MySQL remoto
3. Instalar dependências e rodar o ETL
4. Usar `streamlit run app/app.py --server.port 8501`
