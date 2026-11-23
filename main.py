from interfaces import Arquivista, Scraper, Downloader, Repositor
from interfaces.gerenciador.gerenciador import Gerenciador


def main():

    competencia = "2026-09"

    repositor = Repositor()
    arquivista = Arquivista()
    scraper = Scraper()
    downloader = Downloader()

    gerenciador = Gerenciador(scraper=scraper, arquivista=arquivista, downloader=downloader, repositor=repositor)

    # 1. Consultar arquivos disponíveis na Receita
    gerenciador.verificar_dados_remotos(
        competencia
    )

    # 2. Registrar metadados no PostgreSQL
    quantidade = gerenciador.registrar_arquivos_remotos()

    print(f"Arquivos remotos registrados: {quantidade}")

    # 3. Consultar downloads pendentes
    pendentes = gerenciador.verificar_downloads_pendentes(
        competencia
    )

    print(f"Downloads pendentes: {len(pendentes)}")

    # 4. Processar fila
    gerenciador.processar_fila_downloads(
        competencia=competencia,
        arquivos_pendentes=pendentes
    )


if __name__ == "__main__":
    main()