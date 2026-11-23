import pandas as pd
import requests
import xml.etree.ElementTree as ET


class Scraper:
    def __init__(self):
        pass

    def verificar_dados_remotos(self, data_do_arquivo) -> pd.DataFrame:
        '''
        Essa função cria um data frame com os dados do XML da pasta de dados abertos da Receita
        buscando pela URL e a data "aaaa-mm" para encontrar a pasta com os dados em zip

        '''

        dados = pd.DataFrame(
            columns=[
                'competencia',
                'arquivo',
                'tamanho_mb',
                'modificacao',
                'etag'
            ]
        )
        
        url = (
            "https://arquivos.receitafederal.gov.br"
            "/public.php/dav/files/YggdBLfdninEJX9/"
            f"{data_do_arquivo}/"
        )

        response = requests.request(
            "PROPFIND",
            url,
            headers={"Depth": "1"},
            timeout=60
        )

        response.raise_for_status()

        root = ET.fromstring(response.content)

        ns = {"d": "DAV:"}

        arquivos = []

        for item in root.findall("d:response", ns):

            caminho = item.findtext("d:href", namespaces=ns)

            tamanho = item.findtext(
                ".//d:getcontentlength",
                namespaces=ns
            )

            modificacao = item.findtext(
                ".//d:getlastmodified",
                namespaces=ns
            )

            etag = item.findtext(
                ".//d:getetag",
                namespaces=ns
            )

            if tamanho is None:
                continue

            arquivos.append({
                "competencia": data_do_arquivo,
                "arquivo": caminho.split("/")[-1],
                "tamanho_mb": round(int(tamanho) / 1024**2, 2),
                "modificacao": modificacao,
                "etag": etag
            })

        novos_dados = pd.DataFrame(arquivos)

        return pd.DataFrame(
            arquivos,
            columns=[
                'competencia',
                'arquivo',
                'tamanho_mb',
                'modificacao',
                'etag'
            ]
)
