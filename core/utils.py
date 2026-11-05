from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Recife")

SECOES = [
    "ENFERMARIA","FUSEX","SVP (OPIP)", "SECRETARIA","PRM","SFPC","IDENTIFICAÇÃO","ALMOXARIFADO",
    "FISCAL ADM","TESOURARIA","SALC","SAAJ","CONFORMIDADE","AUDITÓRIO","SPP",
    "S1","S2","S3","S4","GARAGEM","RANCHO","CANTINA","BANDA",
    "1ª CIA","2ª CIA","3ª CIA","CCAP","B ADM"
]

CRACHA_TIPOS = [("MDR", "Mil. Reserva"), ("FUS", "FUSEX"), ("VIS", "Visitante")]

MESES = ['janeiro','fevereiro','março','abril','maio','junho',
         'julho','agosto','setembro','outubro','novembro','dezembro']
DIAS_SEMANA = ['Segunda-feira','Terça-feira','Quarta-feira','Quinta-feira',
               'Sexta-feira','Sábado','Domingo']


def agora_recife() -> datetime:
    """Hora atual no fuso de Recife, independente do fuso do servidor (Vercel = UTC)."""
    return datetime.now(TZ)


def hoje_recife() -> str:
    """Data de hoje (America/Recife) no formato ISO YYYY-MM-DD."""
    return agora_recife().date().isoformat()


def hora_recife() -> str:
    """Hora atual (America/Recife) no formato HH:MM."""
    return agora_recife().strftime('%H:%M')


def formatar_documento(doc):
    """CPF (000.000.000-00) ou RG (00.000.000) conforme qtde de dígitos."""
    if not doc:
        return doc
    digits = ''.join(c for c in str(doc) if c.isdigit())
    if len(digits) in (10, 11):
        digits = digits.zfill(11)
        return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
    elif len(digits) in (7, 8):
        digits = digits.zfill(8)
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}"
    return doc


def formatar_telefone(tel):
    """Telefone no padrão 0 0000-0000 (8 ou 9 dígitos)."""
    if not tel:
        return tel
    digits = ''.join(c for c in str(tel) if c.isdigit())
    if len(digits) in (8, 9):
        digits = digits.zfill(9)
        return f"{digits[0]} {digits[1:5]}-{digits[5:9]}"
    return tel


def formatar_data_extenso(data_iso):
    try:
        d = datetime.strptime(data_iso, '%Y-%m-%d')
        return {
            'dia': str(d.day).zfill(2),
            'mes': MESES[d.month - 1],
            'ano': str(d.year)[-2:],
            'dia_semana': DIAS_SEMANA[d.weekday()],
        }
    except Exception:
        return {'dia': '', 'mes': '', 'ano': '', 'dia_semana': ''}
