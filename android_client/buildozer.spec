[app]
title = FreedomLink
package.name = freedomlink
package.domain = org.freedomlink

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,json,enc

version = 1.7.0
# ✅ Рабочий набор для Python 3.10 + Ubuntu 22.04
requirements = python3,kivy==2.2.1,cryptography==41.0.7,openssl==1.1.1w,android,plyer,websockets==11.0.3,cython<3.0,pyjnius==1.6.1

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.entry_point = org.kivy.android.PythonActivity
android.app_bundle = False
android.archs = arm64-v8a,armeabi-v7a

[buildozer]
p4a.local-recipes = ./local_recipes
p4a.branch = develop