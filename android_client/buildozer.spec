[app]
title = FreedomLink
package.name = freedomlink
package.domain = org.freedomlink

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,json,enc

version = 1.7.0

# ✅ ПОЛНЫЙ набор: включая cryptography с шифрованием
# Версии подобраны так, чтобы работать вместе:
# - cryptography 41.0.7: последний стабильный с C-бэкендом (проще компилировать)
# - openssl 1.1.1w: LTS версия, проверенная в p4a
# - cython<3.0: обязателен для совместимости с pyjnius
requirements = python3,kivy==2.2.1,cryptography==41.0.7,openssl==1.1.1w,android,plyer,websockets==11.0.3,cython<3.0,pyjnius==1.6.1

orientation = portrait
fullscreen = 0

# --- ANDROID SETTINGS ---
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.app_bundle = False

# --- P4A SETTINGS ---
# master ветка: содержит свежие фиксы для Python 3.11 и NDK 25b
p4a.branch = master
# Критично: отключаем авто-добавление libffi в requirements (p4a сам подтянет)
p4a.blacklist_reqs = libffi

# --- DEBUG ---
log_level = 2

[buildozer]
warn_on_root = 1