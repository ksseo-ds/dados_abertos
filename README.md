# Dados Abertos — CNPJ (Receita Federal)

Pipeline ETL em **Python** para consultar, baixar, extrair e importar dados públicos do Cadastro Nacional da Pessoa Jurídica (CNPJ) disponibilizados pela Receita Federal do Brasil (RFB).

O projeto identifica arquivos novos ou modificados por competência, organiza uma fila de processamento, registra a execução e carrega os dados em **PostgreSQL**.

> **Status:** em desenvolvimento. O repositório contém a implementação do pipeline, mas não disponibiliza scripts DDL de inicialização do banco nem testes automatizados.

## Tecnologias

- **Python** — processamento e orquestração.
- **requests + WebDAV** — consulta de metadados por `PROPFIND` e download HTTP.
- **pandas** — manipulação dos metadados e organização da fila.
- **PostgreSQL + psycopg2** — carga de dados e persistência dos controles.
- **python-dotenv** — configuração das credenciais.
- **tqdm** — barras de progresso dos downloads.

## Arquitetura

```text
                         main.py
                            |
                       Gerenciador
                            |
          +-----------------+------------------+
          |                 |                  |
        Scraper          Downloader          Repositor
          |                 |                  |
    Consulta WebDAV     Download ZIP       Extrai CSV
    (metadados)          (.part)          e limpa arquivos
          |                 |                  |
          +-----------------+------------------+
                            |
                        Arquivista
                            |
                        PostgreSQL
                            |
                   +--------+--------+
                   |                 |
                controle       receita_federal
                   |                 |
             arquivos_remotos   tabelas CNPJ
             downloads          e auxiliares
             execucoes
             importacoes
```

### Componentes

| Componente | Responsabilidade |
| --- | --- |
| `Scraper` | Consulta a pasta da competência da RFB por WebDAV e obtém nome, tamanho, modificação e ETag de cada arquivo. |
| `Gerenciador` | Coordena a fila de processamento e a sequência de download e importação. |
| `Downloader` | Baixa arquivos em streaming e usa extensão `.part` até a transferência terminar. |
| `Repositor` | Verifica e extrai ZIPs, padroniza nomes dos CSVs e remove arquivos locais após a importação. |
| `Arquivista` | Gerencia operações no PostgreSQL, controles de execução e cargas dos CSVs. |

## Fluxo do pipeline

1. Consultar arquivos disponíveis para uma competência no formato `AAAA-MM`.
2. Registrar ou atualizar metadados no schema `controle`.
3. Identificar arquivos ainda não baixados, com erro ou com ETag diferente do registrado.
4. Ordenar a fila conforme a prioridade dos conjuntos de dados.
5. Registrar a execução e baixar cada arquivo ZIP.
6. Extrair os arquivos CSV e determinar sua tabela de destino.
7. Importar os dados para o PostgreSQL e registrar o resultado da carga.
8. Excluir os arquivos locais após o processamento e encerrar a execução.

**Prioridade de processamento configurada:** CNAEs → Municípios → Naturezas jurídicas → Qualificações → Países → Motivos → Empresas → Estabelecimentos → Sócios → Simples.

A rotina genérica de importação usa `COPY` para uma tabela temporária seguido de `UPSERT` (`INSERT ... ON CONFLICT DO UPDATE`). Há também uma rotina específica de importação de empresas.

## Estrutura do projeto

```text
dados_abertos/
├── main.py
├── requirements.txt
├── .gitignore
├── interfaces/
│   ├── __init__.py
│   ├── webscrapper/
│   │   └── scraper.py
│   ├── gerenciador/
│   │   └── gerenciador.py
│   ├── downloader/
│   │   └── downloader.py
│   ├── repositor/
│   │   └── repositor.py
│   └── arquivista/
│       └── arquivista.py
└── downloads/         # criada em execução; ignorada pelo Git
```

## Instalação

**Pré-requisitos:** Python compatível com as dependências do projeto, PostgreSQL e acesso à internet. Os schemas e tabelas exigidos pela aplicação devem ser criados antes da primeira execução; seus scripts de criação ainda não estão versionados no repositório.

```bash
git clone https://github.com/ksseo-ds/dados_abertos.git
cd dados_abertos
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz do projeto:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dados_abertos
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
```

O `.env` está no `.gitignore`; **não compartilhe credenciais reais**.

Defina a competência a processar em `main.py`:

```python
competencia = "2026-09"  # exemplo
```

Depois, execute a partir da raiz do projeto:

```bash
python main.py
```

> **Atenção:** as bases oficiais podem demandar vários gigabytes de armazenamento. Verifique espaço disponível, capacidade do banco e estrutura das tabelas antes de realizar uma carga completa.

## Estrutura de dados

A implementação trabalha com dois schemas:

- **`controle`** — `arquivos_remotos`, `downloads`, `execucoes` e `importacoes`, responsáveis pelos metadados e pelo acompanhamento operacional.
- **`receita_federal`** — tabelas como `cnaes`, `municipios`, `naturezas_juridicas`, `qualificacoes`, `paises`, `motivos`, `empresas`, `estabelecimentos`, `socios` e `simples`.

As colunas e os destinos estão definidos no dicionário `Gerenciador.MAPEAMENTO_TABELAS`. As restrições e chaves da base devem ser compatíveis com as instruções de carga do projeto.

## Fonte dos dados

Os arquivos são consultados no [repositório de arquivos da Receita Federal](https://arquivos.receitafederal.gov.br/) por meio de uma interface WebDAV pública.

Este é um projeto independente, sem vínculo com a Receita Federal. O uso dos dados deve observar a legislação aplicável, inclusive a LGPD.

## Limitações e melhorias futuras

- Incluir scripts DDL e instruções para inicialização do PostgreSQL.
- Criar testes automatizados para consulta, fila, download e importação.
- Permitir definir a competência pela linha de comando ou por variável de ambiente.
- Aprimorar o tratamento de falhas entre download, importação e limpeza de arquivos.
- Evoluir a observabilidade e o acompanhamento das execuções.

## Autor

Desenvolvido por [ksseo-ds](https://github.com/ksseo-ds).

## Licença

Consulte o arquivo [LICENSE](LICENSE) do repositório.
