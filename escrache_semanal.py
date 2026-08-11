import os
import requests
from datetime import datetime, timedelta
from slack_sdk import WebClient

# --- CONFIGURACIÓN ---
# Los tokens se leen desde variables de entorno (GitHub Secrets), nunca hardcodeados en el código.
SLACK_TOKEN = os.environ["SLACK_TOKEN"]
TEMPO_TOKEN = os.environ["TEMPO_TOKEN"]

CANAL_SOPORTE = "C04RHGJ0VHA"
CANAL_PROYECTO = "C08CUTDAMHS"

EQUIPO_SOPORTE = {
    "cmillan@wodobox.com": "88e3bd0c-c5ed-490a-b7bc-7e0d1ab04a17",
    "ccarriel@wodobox.com": "712020:3475eed9-0c6d-4d92-bd8e-f02f1cf37766",
    "fmunoz@wodobox.com": "712020:27045643-7d23-4ae8-aa9c-ccf0e438742c",
    "mgarin@wodobox.com": "712020:2fca042c-515d-4eac-96cf-44b50817272d",
    "mmolina@wodobox.com": "712020:082212fc-367e-415a-b854-1038f4df866a",
    "wcartaya@wodobox.com": "712020:e76d1fd3-ab10-4d60-b2db-b4e6c9157c20"
}

EQUIPO_PROYECTO = {
    "cdavalos@wodobox.com": "712020:9afd31ce-74b6-4e1b-bda0-9f2fbac29056",
    "jmcosceri@wodobox.com": "712020:46b2b26b-dd9a-4695-b900-945190f3b3e0",
    "aduarte@wodobox.com": "620128185d18ad0072989cd8",
    "lgalviz@wodobox.com": "712020:1e705a47-f4af-4f37-ab34-18ccc52070af",
    "jazuaje@wodobox.com": "62a770fd979e6e0069042afb",
    "jfredes@wodobox.com": "712020:19911696-3927-4c29-aeb2-f73e87a309d4",
    "ggautier@wodobox.com": "70121:835c793a-ff75-4069-a3c1-8d1f6ed5285e"
}

client = WebClient(token=SLACK_TOKEN)

def calcular_rango_fechas():
    hoy = datetime.now()
    if hoy.weekday() in [0, 5, 6]:
        if hoy.weekday() == 0:
            lunes_semana = hoy - timedelta(days=7)
        elif hoy.weekday() == 5:
            lunes_semana = hoy - timedelta(days=5)
        else:
            lunes_semana = hoy - timedelta(days=6)
        desde_dt = lunes_semana
        hasta_dt = lunes_semana + timedelta(days=4)
    else:
        desde_dt = hoy - timedelta(days=hoy.weekday())
        hasta_dt = hoy
    return {
        "desde_tempo": desde_dt.strftime('%Y-%m-%d'),
        "hasta_tempo": hasta_dt.strftime('%Y-%m-%d'),
        "desde_latam": desde_dt.strftime('%d/%m/%Y'),
        "hasta_latam": hasta_dt.strftime('%d/%m/%Y'),
    }

def obtener_horas_usuario(jira_id, desde_tempo, hasta_tempo):
    url = "https://api.tempo.io/4/worklogs/search"
    headers = {"Authorization": f"Bearer {TEMPO_TOKEN}", "Content-Type": "application/json"}
    id_limpio = jira_id.replace("712020:", "")
    variantes = [f"712020:{id_limpio}", id_limpio]
    horas_usuario = 0.0
    worklogs_vistos = set()
    for v_id in variantes:
        query = {"from": desde_tempo, "to": hasta_tempo, "authorIds": [v_id]}
        try:
            res = requests.post(url, json=query, headers=headers, timeout=15)
            if res.status_code == 200:
                results = res.json().get('results', [])
                for wl in results:
                    wl_id = wl.get('tempoWorklogId')
                    if wl_id not in worklogs_vistos:
                        segundos = wl.get('timeSpentSeconds', 0)
                        horas_usuario += (segundos / 3600)
                        worklogs_vistos.add(wl_id)
        except Exception:
            continue
    return horas_usuario

def auditar_equipo(nombre_equipo, equipo, canal, fechas):
    print(f"\n--- Auditando equipo: {nombre_equipo} ---")
    lista_deudores = []
    for email, jira_id in equipo.items():
        horas_usuario = obtener_horas_usuario(jira_id, fechas["desde_tempo"], fechas["hasta_tempo"])
        if horas_usuario < 40:
            try:
                user_info = client.users_lookupByEmail(email=email)
                slack_mention = f"<@{user_info['user']['id']}>"
                lista_deudores.append(f"• {slack_mention} cargó *{horas_usuario:.1f} hs*")
            except Exception:
                nombre = email.split('@')[0].capitalize()
                lista_deudores.append(f"• *{nombre}* cargó *{horas_usuario:.1f} hs*")
    if lista_deudores:
        mensaje = (f"📢 *REPORTE TEMPO - {nombre_equipo}*\n"
                   f"Periodo auditado: _{fechas['desde_latam']} al {fechas['hasta_latam']}_\n"
                   f"Usuarios con menos de 40hs:\n\n" +
                   "\n".join(lista_deudores) +
                   "\n\n_Por favor, pónganse al día 🫡_")
        try:
            client.chat_postMessage(channel=canal, text=mensaje)
            print(f"✅ Reporte de {nombre_equipo} enviado a Slack.")
        except Exception as e:
            print(f"❌ Error Slack ({nombre_equipo}): {e}")
    else:
        print(f"✅ Todo el equipo de {nombre_equipo} está al día. No se enviará escrache.")

def escrache_semanal():
    hoy = datetime.now()
    fechas = calcular_rango_fechas()
    print(f"\n[{hoy.strftime('%d/%m %H:%M')}] --- INICIANDO AUDITORÍA ---")
    print(f"Buscando logs desde {fechas['desde_latam']} hasta {fechas['hasta_latam']}")
    auditar_equipo("SOPORTE", EQUIPO_SOPORTE, CANAL_SOPORTE, fechas)
    auditar_equipo("PROYECTO", EQUIPO_PROYECTO, CANAL_PROYECTO, fechas)

if __name__ == "__main__":
    escrache_semanal()
