                    GERENCIADOR
                         |
         +---------------+---------------+
         |               |               |
      SCRAPER        DOWNLOADER       REPOSITOR
         |               |               |
   Consulta RFB       Baixa ZIP       Extrai CSV
                         |
                         |
                     ARQUIVISTA
                         |
                    PostgreSQL
                         |
             +-----------+-----------+
             |                       |
           controle             receita_federal
             |                       |
       ├── execucoes            ├── municipios
       ├── downloads            ├── cnaes
       ├── importacoes          ├── empresas
       └── arquivos_remotos     └── ...