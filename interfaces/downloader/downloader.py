import requests
from pathlib import Path
from tqdm import tqdm


class Downloader:

    def download(self, competencia: str, nome_arquivo: str, url: str) -> Path:

        # pasta raiz do projeto
        raiz_projeto = Path(__file__).resolve().parent.parent.parent

        # pasta de destino
        caminho_descarga = raiz_projeto / "downloads" / competencia

        # Cria a pasta para o download
        caminho_descarga.mkdir(parents=True, exist_ok=True)

        # Caminho completo do arquivo
        caminho_arquivo = caminho_descarga / nome_arquivo

        # Caminho temporário durante a transferência
        caminho_temporario = caminho_descarga / f"{nome_arquivo}.part"

        try:
            with requests.get(url, stream=True, timeout=(30, 120)) as response:

                response.raise_for_status()

                tamanho_total = int(response.headers.get("content-length", 0))

                with tqdm(
                    total=tamanho_total or None,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=nome_arquivo
                ) as progresso:

                    with open(caminho_temporario, "wb") as arquivo:

                        for bloco in response.iter_content(
                            chunk_size=1024 * 1024
                        ):
                            if bloco:
                                arquivo.write(bloco)
                                progresso.update(len(bloco))
                            

            # Só disponibiliza o ZIP após concluir a transferência
            caminho_temporario.replace(caminho_arquivo)

            return caminho_arquivo

        except Exception:
            caminho_temporario.unlink(missing_ok=True)
            raise