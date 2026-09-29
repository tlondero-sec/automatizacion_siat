import json
import logging
import os
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def parse_monto(texto):
    if not texto:
        return 0.0
    limpio = re.sub(r"[^\d,]", "", texto).replace(".", "").replace(",", ".")
    return float(limpio) if limpio else 0.0


def sanitizar_nombre(nombre):
    """Limpia caracteres inválidos para nombres de archivos en Windows."""
    return re.sub(r'[\\/*?:"<>|]', "_", nombre)


# Directorio de descargas
dir_descargas = os.path.join(os.getcwd(), "boletas_descargadas")
os.makedirs(dir_descargas, exist_ok=True)

chrome_opts = webdriver.ChromeOptions()
chrome_opts.add_experimental_option(
    "prefs",
    {
        "download.default_directory": dir_descargas,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
    },
)

with open("propiedades.json", "r", encoding="utf-8") as f:
    propiedades = json.load(f)

# Configuración de las dos tasas del SIAT
tasas = [
    {"nombre": "TGI", "id": "14"},
    {"nombre": "TSS", "id": "58"},
]

driver = webdriver.Chrome(options=chrome_opts)
driver.maximize_window()

driver.execute_cdp_cmd(
    "Page.setDownloadBehavior",
    {"behavior": "allow", "downloadPath": dir_descargas},
)

try:
    for prop in propiedades:
        for tasa in tasas:
            id_prop_base = prop["id_propiedad"]
            tasa_nombre = tasa["nombre"]
            id_tasa = tasa["id"]

            nombre_identificador = sanitizar_nombre(
                f"{id_prop_base}_{tasa_nombre}"
            )

            logging.info(
                f"=== Procesando: {nombre_identificador} (Tasa ID: {id_tasa}) ==="
            )

            url_inicio = f"https://siat.parana.gob.ar/siat/seg/Login.do?method=anonimo&url=/gde/AdministrarLiqDeuda.do?method=inicializarContr&id={id_tasa}"
            driver.get(url_inicio)
            wait = WebDriverWait(driver, 15)

            # 1. Credenciales
            input_cuenta = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//label[contains(., 'Cuenta')]/input | //input[contains(@name, 'numeroCuenta')]",
                    )
                )
            )
            input_cuenta.clear()
            input_cuenta.send_keys(prop["numero_cuenta"])

            input_cod = driver.find_element(
                By.XPATH,
                "//label[contains(., 'Cod.')]/input | //input[contains(@name, 'codGesPer')]",
            )
            input_cod.clear()
            input_cod.send_keys(prop["codigo_gestion"])

            driver.find_element(
                By.XPATH, "//*[@id='contenido']/fieldset/div/button"
            ).click()

            # 2. Carga de tabla de resultados
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "tableDeuda"))
            )
            time.sleep(2)

            # 3. Lectura del Total General
            try:
                txt_total = driver.find_element(
                    By.XPATH, "//*[contains(text(), 'Total:')]"
                ).text
                monto_total = parse_monto(txt_total.split("Total:")[-1])
                logging.info(f"Total en encabezado: {txt_total}")
            except Exception:
                monto_total = 0.0

            # 4. Análisis de la primera fila
            filas = driver.find_elements(
                By.XPATH, "//table[contains(@class, 'tableDeuda')]/tbody/tr[td]"
            )

            if filas:
                cols = filas[0].find_elements(By.TAG_NAME, "td")
                periodo_raw = cols[3].text.strip()
                periodo = periodo_raw.replace("/", "-")

                txt_monto = ""
                for c in cols:
                    if "$" in c.text:
                        txt_monto = c.text.strip()
                        break

                monto_ultima_boleta = parse_monto(txt_monto)
                logging.info(f"Boleta período {periodo_raw}: {txt_monto}")

                # Evaluación de Deuda
                if monto_total > monto_ultima_boleta:
                    logging.warning(
                        f"⚠️ ALERTA: {nombre_identificador} posee períodos pendientes acumulados."
                    )
                else:
                    logging.info(f"✅ OK: {nombre_identificador} al día.")

                if monto_ultima_boleta == 0.0 and monto_total == 0.0:
                    logging.info(
                        "Importe $0.00. Se omite la descarga de boleta."
                    )
                    continue

                # 5. Seleccionar la casilla (#admin)
                logging.info("Marcando casilla de selección (#admin)...")
                chk_admin = wait.until(
                    EC.element_to_be_clickable((By.ID, "admin"))
                )
                if not chk_admin.is_selected():
                    chk_admin.click()

                # 6. Clic en 'Impresión de Boleta Digital'
                logging.info(
                    "Haciendo clic en 'Impresión de Boleta Digital'..."
                )
                btn_boleta = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//*[@id='filter']/fieldset[3]/p/button[1] | //button[contains(., 'Impresión de Boleta Digital')]",
                        )
                    )
                )
                btn_boleta.click()

                # 7. Clic en el botón final 'Imprimir Recibo'
                logging.info(
                    "Navegando a reconfección. Buscando 'Imprimir Recibo'..."
                )
                btn_recibo = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//*[@id='filter']/div[3]/button | //button[contains(., 'Imprimir Recibo')]",
                        )
                    )
                )

                # Registrar archivos antes de la descarga para detectar el nuevo
                archivos_antes = set(os.listdir(dir_descargas))
                btn_recibo.click()

                logging.info("Esperando descarga del PDF...")
                time.sleep(5)

                # 8. Renombrar archivo descargado ('recibo...pdf' -> 'NOMBRE_PROP_TASA_PERIODO.pdf')
                archivos_despues = set(os.listdir(dir_descargas))
                nuevos_archivos = archivos_despues - archivos_antes

                for arch in nuevos_archivos:
                    if arch.endswith(".pdf"):
                        ruta_origen = os.path.join(dir_descargas, arch)
                        nuevo_nombre = f"{nombre_identificador}_{periodo}.pdf"
                        ruta_destino = os.path.join(
                            dir_descargas, nuevo_nombre
                        )

                        # Si ya existe un archivo con ese nombre, lo reemplaza de forma limpia
                        if os.path.exists(ruta_destino):
                            os.remove(ruta_destino)

                        os.rename(ruta_origen, ruta_destino)
                        logging.info(f"📄 Boleta guardada como: {nuevo_nombre}")

            else:
                logging.error("No se encontraron registros de deuda.")

            os.makedirs("capturas", exist_ok=True)
            driver.save_screenshot(f"capturas/{nombre_identificador}.png")

finally:
    driver.quit()
    logging.info("Proceso completado para todas las propiedades.")