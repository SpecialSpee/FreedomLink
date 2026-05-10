[app]
title = FreedomLink
package.name = freedomlink
package.domain = org.freedomlink

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,json,enc

version = 1.7.0
requirements = python3,kivy,cryptography,openssl,android,plyer,websockets

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