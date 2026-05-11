[app]
title = FreedomLink
package.name = freedomlink
package.domain = org.freedomlink

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,json

version = 1.0.0
requirements = python3,kivy==2.2.1,cryptography==41.0.7,openssl==1.1.1w,android,plyer,websockets==11.0.3,cython<3.0,pyjnius==1.6.1

orientation = portrait
fullscreen = 0

# --- ANDROID SETTINGS (КРИТИЧНО) ---
android.api = 31
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

# --- BUILD SETTINGS ---
# Используем стабильную ветку p4a, где фиксы уже есть
p4a.branch = stable

# --- DEBUG ---
log_level = 2

[buildozer]
warn_on_root = 1