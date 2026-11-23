from pathlib import Path
from interfaces import Arquivista, Scraper, Downloader, Repositor
import pandas as pd

class Gerenciador():
    def __init__(self, scraper:Scraper, arquivista:Arquivista, downloader:Downloader, repositor:Repositor):
        self.scraper = scraper
        self.arquivista = arquivista
        self.downloader = downloader
        self.repositor = repositor
        self.dados_remotos = None
        
        self.PRIORIDADE_CONJUNTOS = {
        "Cnaes": 1,
        "Municipios": 2,
        "Naturezas": 3,
        "Qualificacoes": 4,
        "Paises": 5,
        "Motivos": 6,
        "Empresas": 7,
        "Estabelecimentos": 8,
        "Socios": 9,
        "Simples": 10
        }
        self.MAPEAMENTO_TABELAS = {

            "Cnaes": {
                "tabela": "cnaes",
                "colunas": [
                    "codigo",
                    "descricao"
                ]
            },

            "Municipios": {
                "tabela": "municipios",
                "colunas": [
                    "codigo",
                    "descricao"
                ]
            },

            "Naturezas": {
                "tabela": "naturezas_juridicas",
                "colunas": [
                    "codigo",
                    "descricao"
                ]
            },

            "Qualificacoes": {
                "tabela": "qualificacoes",
                "colunas": [
                    "codigo",
                    "descricao"
                ]
            },

            "Paises": {
                "tabela": "paises",
                "colunas": [
                    "codigo",
                    "descricao"
                ]
            },

            "Motivos": {
                "tabela": "motivos",
                "colunas": [
                    "codigo",
                    "descricao"
                ]
            },

            "Empresas": {
                "tabela": "empresas",
                "colunas": [
                    "cnpj_basico",
                    "razao_social",
                    "natureza_juridica",
                    "qualificacao_responsavel",
                    "capital_social",
                    "porte_empresa",
                    "ente_federativo_responsavel"
                ]
            },

            "Estabelecimentos": {
                "tabela": "estabelecimentos",
                "colunas": [
                    "cnpj_basico",
                    "cnpj_ordem",
                    "cnpj_dv",
                    "identificador_matriz_filial",
                    "nome_fantasia",
                    "situacao_cadastral",
                    "data_situacao_cadastral",
                    "motivo_situacao_cadastral",
                    "nome_cidade_exterior",
                    "pais",
                    "data_inicio_atividade",
                    "cnae_fiscal_principal",
                    "cnae_fiscal_secundaria",
                    "tipo_logradouro",
                    "logradouro",
                    "numero",
                    "complemento",
                    "bairro",
                    "cep",
                    "uf",
                    "municipio",
                    "ddd_1",
                    "telefone_1",
                    "ddd_2",
                    "telefone_2",
                    "ddd_fax",
                    "fax",
                    "correio_eletronico",
                    "situacao_especial",
                    "data_situacao_especial"
                ]
            },

            "Socios": {
                "tabela": "socios",
                "colunas": [
                    "cnpj_basico",
                    "identificador_socio",
                    "nome_socio",
                    "cnpj_cpf_socio",
                    "qualificacao_socio",
                    "data_entrada_sociedade",
                    "pais",
                    "representante_legal",
                    "nome_representante",
                    "qualificacao_representante",
                    "faixa_etaria"
                ]
            },

            "Simples": {
                "tabela": "simples",
                "colunas": [
                    "cnpj_basico",
                    "opcao_pelo_simples",
                    "data_opcao_simples",
                    "data_exclusao_simples",
                    "opcao_pelo_mei",
                    "data_opcao_mei",
                    "data_exclusao_mei"
                ]
            }
        }
    #funções de scraper 
    def verificar_dados_remotos(self, data_do_arquivo:str):
        '''
        Função utiliza o scraper passado ao gerenciador para recuperar os nomes dos arquivos de dados abertos, e insere o retorno como atributo do gerenciador

        o atributo pe um pandas.DataFrame
        '''
        self.dados_remotos = self.scraper.verificar_dados_remotos(data_do_arquivo)

    #funções de Arquivista
    def registrar_arquivos_remotos(self):
        if self.dados_remotos is None:
            raise ValueError("Nenhuma consulta remota foi realizada.")

        return self.arquivista.registrar_arquivos_remotos(
            self.dados_remotos
        )

    def verificar_downloads_pendentes(self, competencia: str):
        '''
        Função verifica o banco para identificar arquivos que não foram baixados ainda

        '''
        return self.arquivista.consultar_downloads_pendentes(
            competencia
        )

    # funções de Downloader
    def efetuar_download(self, competencia: str, nome_arquivo: str, url: str) -> Path:

        caminho_arquivo = self.downloader.download(
            competencia=competencia,
            nome_arquivo=nome_arquivo,
            url=url
        )

        return caminho_arquivo 
    
    def organizar_fila_downloads(self, arquivos_pendentes)->pd.DataFrame:
        """
        Recebe os arquivos pendentes e retorna
        um DataFrame ordenado conforme a prioridade
        dos conjuntos de dados.
        """


        if arquivos_pendentes.empty:
            return arquivos_pendentes.copy()

        fila = arquivos_pendentes.copy()


        def identificar_prioridade(nome_arquivo):

            for prefixo, prioridade in self.PRIORIDADE_CONJUNTOS.items():

                if nome_arquivo.lower().startswith(prefixo.lower()):
                    return prioridade

            return 999

        fila["prioridade"] = fila["nome_arquivo"].apply(
            identificar_prioridade
        )

        fila = fila.sort_values(
            by=["prioridade", "nome_arquivo"],
            ascending=True,
            kind="stable"
        )

        return fila.reset_index(drop=True)

    #Funções de importação 
    def processar_importacao(self, execucao_id: int, download_id: int, caminho_csv: Path, tabela: str, colunas: list[str]) -> int:
        """
        Gerencia o processo de importação de um CSV.

        Registra o início, executa a importação e
        registra a conclusão ou o erro.
        """

        importacao_id = self.arquivista.registrar_importacao(
            execucao_id=execucao_id,
            download_id=download_id
        )

        try:
            if tabela == "empresas":

                quantidade = self.arquivista.importar_empresas(
                    caminho_csv=caminho_csv
                )

            else:

                quantidade = self.arquivista.importar_csv(
                    caminho_csv=caminho_csv,
                    schema="receita_federal",
                    tabela=tabela,
                    colunas=colunas
                )

            atualizado = self.arquivista.finalizar_importacao(
                importacao_id=importacao_id,
                status="CONCLUIDO",
                registros_importados=quantidade
            )

            if not atualizado:
                raise RuntimeError(
                    f"Não foi possível finalizar a importação {importacao_id}"
                )

            print(
                f"Importação concluída: {caminho_csv.name} "
                f"({quantidade} registros)"
            )

            return quantidade

        except Exception as erro:

            self.arquivista.finalizar_importacao(
                importacao_id=importacao_id,
                status="ERRO",
                mensagem_erro=str(erro)
            )

            raise

    def identificar_tabela(self, nome_arquivo: str) -> dict | None:

        for prefixo, configuracao in self.MAPEAMENTO_TABELAS.items():

            if nome_arquivo.lower().startswith(prefixo.lower()):
                return configuracao

        return None





    # processo FINAL para iniciar os downloads
    def processar_fila_downloads(
        self,
        competencia: str,
        arquivos_pendentes: pd.DataFrame
    ):

        fila = self.organizar_fila_downloads(
            arquivos_pendentes
        )

        if fila.empty:
            print("Nenhum arquivo pendente.")
            return

        # Uma execução para toda a fila
        execucao_id = self.arquivista.registrar_execucao(
            rotina="DOWNLOAD_RFB"
        )

        try:
            for arquivo in fila.itertuples(index=False):

                print(
                    f"Prioridade {arquivo.prioridade} | "
                    f"{arquivo.nome_arquivo}"
                )

                parametros = {
                    "execucao_id": execucao_id,
                    "arquivo_id": arquivo.arquivo_id,
                    "etag": arquivo.etag
                }

                # 1. Registrar pendência
                registrado = self.arquivista.registrar_download(
                    **parametros,
                    status="PENDENTE"
                )

                if not registrado:
                    print(
                        f"Arquivo já registrado: "
                        f"{arquivo.nome_arquivo}"
                    )
                    # Um registro PENDENTE com o mesmo ETag
                    # também pode retornar False.
                    # Nesse caso, o download ainda deve ocorrer.
                    if arquivo.status != "PENDENTE":
                        continue

                try:
                    # 2. Iniciar download
                    self.arquivista.registrar_download(
                        **parametros,
                        status="EXECUTANDO"
                    )

                    # 3. Baixar arquivo
                    caminho = self.efetuar_download(
                        competencia=competencia,
                        nome_arquivo=arquivo.nome_arquivo,
                        url=arquivo.url
                    )

                    # 4. Registrar conclusão
                    self.arquivista.registrar_download(
                        **parametros,
                        status="CONCLUIDO",
                        caminho_local=str(caminho),
                        tamanho_baixado=caminho.stat().st_size
                    )


                except Exception as erro:

                    self.arquivista.registrar_download(
                        **parametros,
                        status="ERRO",
                        mensagem_erro=str(erro)
                    )

                    raise

                # 5. Extrair o arquivo ZIP
                arquivos_extraidos = self.repositor.extrair_arquivo(
                    caminho_zip=caminho
                )

                # 6. Identificar a tabela de destino
                configuracao = self.identificar_tabela(
                    nome_arquivo=arquivo.nome_arquivo
                )

                if configuracao is None:
                    raise ValueError(
                        f"Tabela não configurada para: {arquivo.nome_arquivo}"
                    )

                # 7. Recuperar o ID do download
                download_id = self.arquivista.consultar_download_id(
                    arquivo_id=arquivo.arquivo_id
                )

                # 8. Importar os arquivos extraídos
                for caminho_csv in arquivos_extraidos:

                    self.processar_importacao(
                        execucao_id=execucao_id,
                        download_id=download_id,
                        caminho_csv=caminho_csv,
                        tabela=configuracao["tabela"],
                        colunas=configuracao["colunas"]
                    )
                # 9. Excluir arquivos após importação concluída
                    self.repositor.excluir_arquivos(
                        caminhos=[*arquivos_extraidos, caminho]
                    )
            # Finalizar execução
            self.arquivista.finalizar_execucao(
                execucao_id=execucao_id,
                status="CONCLUIDO"
            )

        except Exception as erro:

            self.arquivista.finalizar_execucao(
                execucao_id=execucao_id,
                status="ERRO",
                mensagem_erro=str(erro)
            )

            raise