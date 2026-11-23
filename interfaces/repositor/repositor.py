from pathlib import Path
from zipfile import ZipFile, BadZipFile


class Repositor:

    def __init__(self):
        pass

from pathlib import Path
from zipfile import ZipFile, BadZipFile
import shutil


class Repositor:

    def extrair_arquivo(self, caminho_zip: str | Path) -> list[Path]:
        """
        Extrai os arquivos CSV diretamente na pasta do ZIP,
        utilizando nomes padronizados.
        """

        caminho_zip = Path(caminho_zip)

        if not caminho_zip.is_file():
            raise FileNotFoundError(
                f"Arquivo não encontrado: {caminho_zip}"
            )

        diretorio_destino = caminho_zip.parent

        arquivos_extraidos = []

        with ZipFile(caminho_zip, "r") as zip_ref:

            if zip_ref.testzip() is not None:
                raise BadZipFile(
                    f"Arquivo ZIP corrompido: {caminho_zip}"
                )

            membros = [
                membro
                for membro in zip_ref.infolist()
                if not membro.is_dir()
            ]

            for indice, membro in enumerate(membros):

                nome_arquivo = caminho_zip.stem.lower()

                if len(membros) > 1:
                    nome_arquivo += f"_{indice}"

                nome_arquivo += ".csv"

                caminho_destino = (
                    diretorio_destino / nome_arquivo
                )

                if caminho_destino.exists():
                    raise FileExistsError(
                        f"Arquivo já existe: {caminho_destino}"
                    )

                with zip_ref.open(membro) as origem:
                    with caminho_destino.open("xb") as destino:
                        shutil.copyfileobj(
                            origem,
                            destino
                        )

                arquivos_extraidos.append(
                    caminho_destino
                )

        return arquivos_extraidos

    def excluir_arquivos(self, caminhos: list[Path]) -> int:
        """
        Exclui os arquivos informados.

        Retorna a quantidade de arquivos excluídos.
        """

        quantidade = 0

        for caminho in caminhos:

            caminho = Path(caminho)

            if caminho.is_file():
                caminho.unlink()
                quantidade += 1

                print(f"Arquivo excluído: {caminho.name}")

        return quantidade

if __name__ == "__main__":

    repositor = Repositor()

    arquivos = repositor.extrair_arquivo(
        "downloads/2026-09/Municipios.zip"
    )

    for arquivo in arquivos:
        print(
            f"Arquivo extraído: {arquivo.name}"
        )
        print(
            f"Tamanho: {arquivo.stat().st_size} bytes"
        )