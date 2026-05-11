[app]
title = FreedomLink
package.name = freedomlink
package.domain = org.freedomlink
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,json
version = 1.7.0

# ✅ МИНИМАЛЬНЫЙ набор: только чистый Python + Kivy
# Никаких C-библиотек = гарантированная сборка
requirements = python3,kivy==2.2.1,android,plyer,websockets==11.0.3,cython<3.0,pyjnius==1.6.1

orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.app_bundle = False

p4a.branch = master
log_level = 2

[buildozer]
warn_on_root = 1