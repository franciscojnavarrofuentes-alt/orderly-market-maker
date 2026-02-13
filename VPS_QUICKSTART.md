# VPS Quick Start Guide (5 minutos)

## 🚀 Instalación Automática en 3 Comandos

### 1. Conecta a tu VPS

```bash
ssh root@TU_IP_VPS
```

### 2. Descarga y ejecuta el script de instalación

```bash
wget https://raw.githubusercontent.com/franciscojnavarrofuentes-alt/orderly-market-maker/main/vps_setup.sh
sudo bash vps_setup.sh
```

**¡Eso es todo!** El script instalará automáticamente:
- ✅ Python 3.10+ y dependencias
- ✅ Git, screen, htop
- ✅ El bot desde GitHub
- ✅ Virtual environment y paquetes Python
- ✅ Firewall (ufw)
- ✅ Systemd service para auto-start
- ✅ Scripts de manejo (start/stop/status)

### 3. Configura tus credenciales

```bash
nano /root/orderly-market-maker/.env
```

**Edita estas líneas:**
```env
ORDERLY_ACCOUNT_ID=tu_account_id_aqui
ORDERLY_KEY=ed25519:tu_key_aqui
ORDERLY_SECRET=ed25519:tu_secret_aqui

DRY_RUN=true    # ¡Importante! Primero prueba en dry-run
```

Guarda: `Ctrl+X`, luego `Y`, luego `Enter`

---

## 🧪 Paso 4: Probar en DRY_RUN

```bash
cd /root/orderly-market-maker
source .venv/bin/activate
PYTHONPATH=src python3 -m mm.main
```

Deberías ver:
```
Starting Dynamic Loss-Protected Market Maker for PERP_ETH_USDC
Base spread: 18 bps, Size: $60
Strategy: Dynamic loss protection from order #1 + $0.08 take-profit
[DRY RUN] Would place orders
```

Si funciona, presiona `Ctrl+C` para detener.

---

## 🔥 Paso 5: Activar Modo Producción

```bash
nano /root/orderly-market-maker/.env
# Cambia: DRY_RUN=false
# Guarda: Ctrl+X, Y, Enter

# Inicia el bot
/root/mm-start.sh
```

¡El bot ahora está corriendo en producción! 🎉

---

## 📊 Comandos de Manejo

### Ver estado del bot
```bash
/root/mm-status.sh
```

### Ver logs en tiempo real
```bash
tail -f /root/orderly-market-maker/mm_run.log
```

### Detener el bot
```bash
/root/mm-stop.sh
```

### Reiniciar el bot
```bash
/root/mm-stop.sh && /root/mm-start.sh
```

### Ver trades recientes
```bash
grep "✓ TAKE PROFIT\|Position changed" /root/orderly-market-maker/mm_run.log | tail -20
```

---

## 🔄 Actualizar el Bot

```bash
cd /root/orderly-market-maker
git pull origin main
/root/mm-stop.sh
source .venv/bin/activate
pip install -r requirements.txt
/root/mm-start.sh
```

---

## 🛡️ Seguridad

El script ya configuró:
- ✅ Firewall (ufw) con solo SSH permitido
- ✅ .env protegido (chmod 600)
- ✅ Systemd service con auto-restart

**Recomendaciones adicionales:**
1. Cambia el puerto SSH por defecto (22)
2. Desactiva login por contraseña (solo SSH keys)
3. Instala fail2ban

---

## ⚠️ Troubleshooting

### Bot no arranca
```bash
# Ver logs del sistema
sudo journalctl -u mm-bot -n 50

# Verificar servicio
systemctl status mm-bot
```

### Credenciales incorrectas
```bash
nano /root/orderly-market-maker/.env
# Corrige las credenciales
/root/mm-stop.sh && /root/mm-start.sh
```

### Ver uso de recursos
```bash
htop
# Busca el proceso "python"
```

---

## 📈 Monitoreo desde tu Ordenador

Puedes monitorear el bot desde tu Mac/PC:

```bash
# Ver logs remotos
ssh root@TU_IP_VPS "tail -f /root/orderly-market-maker/mm_run.log"

# Ver estado remoto
ssh root@TU_IP_VPS "/root/mm-status.sh"
```

---

## 🎯 Performance Esperado

Con la configuración optimizada (18 bps, $60, $0.08 TP):
- **Win Rate:** >90%
- **Trades/día:** 25-35
- **Profit/día:** $3-5 USD
- **Drawdown máx:** <$1

---

## 📞 Ayuda

Si tienes problemas:
1. Revisa los logs: `tail -f /root/orderly-market-maker/mm_run.log`
2. Verifica estado: `/root/mm-status.sh`
3. Chequea credenciales: `nano /root/orderly-market-maker/.env`
4. Verifica conectividad: `ping api.orderly.org`

---

**¡Listo!** Tu bot está corriendo 24/7 en el VPS. 🚀
