import os
import pandas as pd
import psycopg2
from pathlib import Path
from psycopg2 import sql
from dotenv import load_dotenv


load_dotenv()

class Arquivista():
    def __init__(self):
        self.conexao = None 
        self.DB_HOST = os.getenv('DB_HOST')
        self.DB_PORT=os.getenv('DB_PORT')
        self.DB_NAME=os.getenv('DB_NAME')
        self.DB_USER=os.getenv('DB_USER')
        self.DB_PASSWORD=os.getenv('DB_PASSWORD')

    def conectar(self):
        if self.conexao is None or self.conexao.closed:
            self.conexao = psycopg2.connect(
                host=self.DB_HOST,
                port=self.DB_PORT,
                dbname=self.DB_NAME,
                user=self.DB_USER,
                password=self.DB_PASSWORD
            )
            
        return self.conexao
        
    def fechar_conexao(self):
        if self.conexao is not None and not self.conexao.closed:
            self.conexao.close()

        self.conexao = None

    def registrar_arquivos_remotos(self, df):

        sql = """
            INSERT INTO controle.arquivos_remotos (
                competencia,
                nome_arquivo,
                tamanho_bytes,
                ultima_modificacao,
                etag,
                url
            )
            VALUES (%s, %s, %s, %s, %s, %s)

            ON CONFLICT (competencia, nome_arquivo)
            DO UPDATE SET
                tamanho_bytes = EXCLUDED.tamanho_bytes,
                ultima_modificacao = EXCLUDED.ultima_modificacao,
                etag = EXCLUDED.etag,
                url = EXCLUDED.url,
                identificado_em = NOW();
        """

        if df.empty:
            return 0

        conexao = self.conectar()

        try:
            with conexao.cursor() as cursor:

                for registro in df.itertuples(index=False):

                    tamanho_bytes = round(
                        registro.tamanho_mb * 1024**2
                    )

                    url = (
                        "https://arquivos.receitafederal.gov.br"
                        "/public.php/dav/files/YggdBLfdninEJX9/"
                        f"{registro.competencia}/{registro.arquivo}"
                    )

                    cursor.execute(
                        sql,
                        (
                            registro.competencia,
                            registro.arquivo,
                            tamanho_bytes,
                            registro.modificacao,
                            registro.etag,
                            url
                        )
                    )

            conexao.commit()

            return len(df)

        except Exception:
            conexao.rollback()
            raise

        finally:
            self.fechar_conexao()

    def consultar_downloads_pendentes(self, competencia: str) -> pd.DataFrame:
        '''
        Essa função compara os arquivos remotos e verifica se eles foram baixados.

        '''
        
        sql = """
            SELECT
                a.id AS arquivo_id,
                a.competencia,
                a.nome_arquivo,
                a.url,
                a.etag,
                d.status

            FROM controle.arquivos_remotos a

            LEFT JOIN controle.downloads d
                ON d.arquivo_id = a.id

            WHERE a.competencia = %s

            AND (
                d.id IS NULL
                OR d.status IN ('PENDENTE', 'ERRO')
                OR d.etag_download IS DISTINCT FROM a.etag
            )

            ORDER BY a.nome_arquivo;
        """

        conexao = self.conectar()

        try:
            return pd.read_sql_query(
                sql,
                conexao,
                params=(competencia,)
            )

        finally:
            self.fechar_conexao()   

    def registrar_download(
        self,
        execucao_id: int,
        arquivo_id: int,
        etag: str,
        status: str,
        caminho_local: str = None,
        tamanho_baixado: int = None,
        mensagem_erro: str = None
    ):
        '''
        Essa função altera status do download para os status validos
        
        '''
        status_validos = {
            "PENDENTE",
            "EXECUTANDO",
            "CONCLUIDO",
            "ERRO"
        }

        if status not in status_validos:
            raise ValueError(f"Status inválido: {status}")

        sql = """
            INSERT INTO controle.downloads (
                execucao_id,
                arquivo_id,
                etag_download,
                status,
                inicio,
                fim,
                caminho_local,
                tamanho_baixado,
                mensagem_erro
            )
            VALUES (
                %s, %s, %s, %s,
                CASE WHEN %s = 'EXECUTANDO' THEN NOW() ELSE NULL END,
                CASE WHEN %s IN ('CONCLUIDO', 'ERRO') THEN NOW() ELSE NULL END,
                %s, %s, %s
            )

            ON CONFLICT (arquivo_id)
            DO UPDATE SET
                execucao_id = EXCLUDED.execucao_id,
                etag_download = EXCLUDED.etag_download,
                status = EXCLUDED.status,

                inicio = CASE
                    WHEN EXCLUDED.status = 'PENDENTE' THEN NULL
                    WHEN EXCLUDED.status = 'EXECUTANDO' THEN NOW()
                    ELSE controle.downloads.inicio
                END,

                fim = CASE
                    WHEN EXCLUDED.status IN ('CONCLUIDO', 'ERRO') THEN NOW()
                    ELSE NULL
                END,

                caminho_local = CASE
                    WHEN EXCLUDED.status IN ('PENDENTE', 'EXECUTANDO')
                        THEN NULL
                    ELSE EXCLUDED.caminho_local
                END,

                tamanho_baixado = CASE
                    WHEN EXCLUDED.status IN ('PENDENTE', 'EXECUTANDO')
                        THEN NULL
                    ELSE EXCLUDED.tamanho_baixado
                END,

                mensagem_erro = EXCLUDED.mensagem_erro

            WHERE
                EXCLUDED.status <> 'PENDENTE'
                OR controle.downloads.etag_download
                    IS DISTINCT FROM EXCLUDED.etag_download
                OR controle.downloads.status = 'ERRO';
        """

        conexao = self.conectar()

        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        execucao_id,
                        arquivo_id,
                        etag,
                        status,
                        status,
                        status,
                        caminho_local,
                        tamanho_baixado,
                        mensagem_erro
                    )
                )

                alterado = cursor.rowcount == 1

            conexao.commit()
            return alterado

        except Exception:
            conexao.rollback()
            raise

        finally:
            self.fechar_conexao()


    def registrar_execucao(self, rotina: str) -> int:

        sql = """
            INSERT INTO controle.execucoes (
                rotina,
                inicio,
                status
            )
            VALUES (%s, NOW(), 'EXECUTANDO')
            RETURNING id;
        """

        conexao = self.conectar()

        try:
            with conexao.cursor() as cursor:
                cursor.execute(sql, (rotina,))
                execucao_id = cursor.fetchone()[0]

            conexao.commit()
            return execucao_id

        except Exception:
            conexao.rollback()
            raise

        finally:
            self.fechar_conexao()

    def finalizar_execucao(self, execucao_id: int, status: str, mensagem_erro: str = None) -> bool:

        status_validos = {"CONCLUIDO", "ERRO"}

        if status not in status_validos:
            raise ValueError(f"Status inválido: {status}")

        sql = """
            UPDATE controle.execucoes
            SET
                fim = NOW(),
                status = %s,
                mensagem_erro = %s
            WHERE id = %s
            AND status = 'EXECUTANDO';
        """

        conexao = self.conectar()

        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        status,
                        mensagem_erro,
                        execucao_id
                    )
                )

                atualizado = cursor.rowcount == 1

            conexao.commit()
            return atualizado

        except Exception:
            conexao.rollback()
            raise

        finally:
            self.fechar_conexao()

    #Funcoes de importação de CSV para o Banco de Dados

    def importar_csv(self, caminho_csv: str | Path, schema: str, tabela: str, colunas: list[str]) -> int:
        """
        Importa CSV utilizando COPY + tabela temporária + UPSERT.

        - Registros novos: INSERT
        - Registros existentes: UPDATE
        - Retorna a quantidade de registros inseridos ou atualizados.
        """

        caminho_csv = Path(caminho_csv)

        if not caminho_csv.is_file():
            raise FileNotFoundError(
                f"Arquivo não encontrado: {caminho_csv}"
            )

        if not colunas:
            raise ValueError("Informe as colunas do arquivo CSV.")

        # Chaves utilizadas no ON CONFLICT
        chaves = {
            "cnaes": ["codigo"],
            "municipios": ["codigo"],
            "motivos": ["codigo"],
            "naturezas_juridicas": ["codigo"],
            "paises": ["codigo"],
            "qualificacoes": ["codigo"],
            "empresas": ["cnpj_basico"],
            "estabelecimentos": [
                "cnpj_basico",
                "cnpj_ordem",
                "cnpj_dv"
            ],
            "simples": ["cnpj_basico"]
        }

        if schema != "receita_federal":
            raise ValueError(f"Schema não permitido: {schema}")

        if tabela not in chaves:
            raise ValueError(
                f"UPSERT não configurado para a tabela: {tabela}"
            )

        chave_primaria = chaves[tabela]

        if not set(chave_primaria).issubset(colunas):
            raise ValueError(
                f"Colunas da chave ausentes em {tabela}"
            )

        conexao = self.conectar()

        try:
            with conexao.cursor() as cursor:

                # 1. Criar tabela temporária com a estrutura da tabela destino
                # Todas as colunas são TEXT para facilitar o COPY.

                definicao_colunas = sql.SQL(", ").join(
                    sql.SQL("{} TEXT").format(
                        sql.Identifier(coluna)
                    )
                    for coluna in colunas
                )

                comando_staging = sql.SQL("""
                    CREATE TEMP TABLE staging_importacao (
                        {}
                    ) ON COMMIT DROP
                """).format(definicao_colunas)

                cursor.execute(comando_staging)

                # 2. Importar CSV para a tabela temporária

                comando_copy = sql.SQL("""
                    COPY staging_importacao ({})
                    FROM STDIN
                    WITH (
                        FORMAT CSV,
                        DELIMITER ';',
                        QUOTE '"',
                        ENCODING 'LATIN1',
                        HEADER FALSE
                    )
                """).format(
                    sql.SQL(", ").join(
                        sql.Identifier(coluna)
                        for coluna in colunas
                    )
                )

                with caminho_csv.open("rb") as arquivo:
                    cursor.copy_expert(
                        comando_copy.as_string(conexao),
                        arquivo
                    )

                # 3. Montar conversões para os tipos da tabela destino

                expressoes = []

                for coluna in colunas:

                    if tabela == "empresas" and coluna == "capital_social":

                        expressao = sql.SQL("""
                            NULLIF(
                                REPLACE({}, ',', '.'),
                                ''
                            )::NUMERIC
                        """).format(
                            sql.Identifier(coluna)
                        )

                    else:
                        expressao = sql.Identifier(coluna)

                    expressoes.append(expressao)

                # 4. Montar atualização das colunas não pertencentes à chave

                colunas_atualizacao = [
                    coluna
                    for coluna in colunas
                    if coluna not in chave_primaria
                ]

                atualizacoes = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(coluna),
                        sql.Identifier(coluna)
                    )
                    for coluna in colunas_atualizacao
                )

                # 5. Executar UPSERT

                comando_upsert = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    SELECT {}
                    FROM staging_importacao
                    ON CONFLICT ({})
                    DO UPDATE SET {}
                """).format(
                    sql.Identifier(schema),
                    sql.Identifier(tabela),

                    sql.SQL(", ").join(
                        sql.Identifier(coluna)
                        for coluna in colunas
                    ),

                    sql.SQL(", ").join(expressoes),

                    sql.SQL(", ").join(
                        sql.Identifier(coluna)
                        for coluna in chave_primaria
                    ),

                    atualizacoes
                )

                cursor.execute(comando_upsert)

                quantidade = cursor.rowcount

            conexao.commit()

            return quantidade

        except Exception:
            conexao.rollback()
            raise

        finally:
            self.fechar_conexao()

    def importar_empresas(self, caminho_csv: str | Path) -> int:
        """
        Importa o CSV de empresas da Receita Federal,
        convertendo capital_social para NUMERIC.
        """

        caminho_csv = Path(caminho_csv)

        if not caminho_csv.is_file():
            raise FileNotFoundError(
                f"Arquivo não encontrado: {caminho_csv}"
            )

        conexao = self.conectar()

        try:
            with conexao.cursor() as cursor:

                # 1. Criar tabela temporária
                cursor.execute("""
                    CREATE TEMP TABLE empresas_staging (
                        cnpj_basico TEXT,
                        razao_social TEXT,
                        natureza_juridica TEXT,
                        qualificacao_responsavel TEXT,
                        capital_social TEXT,
                        porte_empresa TEXT,
                        ente_federativo_responsavel TEXT
                    ) ON COMMIT DROP;
                """)

                # 2. Importar CSV sem conversão
                with caminho_csv.open("rb") as arquivo:

                    cursor.copy_expert("""
                        COPY empresas_staging
                        FROM STDIN
                        WITH (
                            FORMAT CSV,
                            DELIMITER ';',
                            QUOTE '"',
                            ENCODING 'LATIN1',
                            HEADER FALSE
                        );
                    """, arquivo)

                # 3. Converter capital_social e inserir na tabela definitiva
                cursor.execute("""
                    INSERT INTO receita_federal.empresas (
                        cnpj_basico,
                        razao_social,
                        natureza_juridica,
                        qualificacao_responsavel,
                        capital_social,
                        porte_empresa,
                        ente_federativo_responsavel
                    )
                    SELECT
                        cnpj_basico,
                        razao_social,
                        natureza_juridica,
                        qualificacao_responsavel,

                        NULLIF(
                            REPLACE(capital_social, ',', '.'),
                            ''
                        )::NUMERIC,

                        porte_empresa,
                        ente_federativo_responsavel

                    FROM empresas_staging

                    ON CONFLICT (cnpj_basico)
                    DO UPDATE SET
                        razao_social = EXCLUDED.razao_social,
                        natureza_juridica = EXCLUDED.natureza_juridica,
                        qualificacao_responsavel = EXCLUDED.qualificacao_responsavel,
                        capital_social = EXCLUDED.capital_social,
                        porte_empresa = EXCLUDED.porte_empresa,
                        ente_federativo_responsavel =
                            EXCLUDED.ente_federativo_responsavel;
                """)

                quantidade = cursor.rowcount

            conexao.commit()

            return quantidade

        except Exception:
            conexao.rollback()
            raise

        finally:
            self.fechar_conexao()


    def registrar_importacao(self, execucao_id: int, download_id: int) -> int:
        """
        Registra o início de uma importação.

        Retorna o ID da importação.
        """

        comando = """
            INSERT INTO controle.importacoes (
                execucao_id,
                download_id,
                inicio,
                status
            )
            VALUES (
                %s,
                %s,
                NOW(),
                'EXECUTANDO'
            )
            RETURNING id;
        """

        conexao = self.conectar()

        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    comando,
                    (execucao_id, download_id)
                )

                importacao_id = cursor.fetchone()[0]

            conexao.commit()

            return importacao_id

        except Exception:
            conexao.rollback()
            raise

        finally:
            self.fechar_conexao()

    def finalizar_importacao(self, importacao_id: int, status: str, registros_importados: int = None, mensagem_erro: str = None) -> bool:

        status_validos = {"CONCLUIDO", "ERRO"}

        if status not in status_validos:
            raise ValueError(f"Status inválido: {status}")

        comando = """
            UPDATE controle.importacoes
            SET
                fim = NOW(),
                status = %s,
                registros_importados = %s,
                mensagem_erro = %s
            WHERE id = %s
            AND status = 'EXECUTANDO';
        """

        conexao = self.conectar()

        try:
            with conexao.cursor() as cursor:

                cursor.execute(
                    comando,
                    (
                        status,
                        registros_importados,
                        mensagem_erro,
                        importacao_id
                    )
                )

                atualizado = cursor.rowcount == 1

            conexao.commit()

            return atualizado

        except Exception:
            conexao.rollback()
            raise

        finally:
            self.fechar_conexao()

    def consultar_download_id(self, arquivo_id: int) -> int:

        comando = """
            SELECT id
            FROM controle.downloads
            WHERE arquivo_id = %s;
        """

        conexao = self.conectar()

        try:
            with conexao.cursor() as cursor:
                cursor.execute(comando, (arquivo_id,))
                resultado = cursor.fetchone()

                if resultado is None:
                    raise ValueError(
                        f"Download não encontrado: arquivo_id={arquivo_id}"
                    )

                return resultado[0]

        finally:
            self.fechar_conexao()

if __name__ == "__main__":
    
    arquivista = Arquivista()

    quantidade = arquivista.importar_csv(
        caminho_csv="downloads/2026-09/municipios.csv",
        schema="receita_federal",
        tabela="municipios",
        colunas=["codigo", "descricao"]
    )

    print(f"Registros importados: {quantidade}")