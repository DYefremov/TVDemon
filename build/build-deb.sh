#!/bin/bash
VER="2.0.0-Alpha2"
B_PATH="dist/TVDemon"

mkdir -p $B_PATH
cp -TRv debian "$B_PATH/DEBIAN"
rsync --exclude=__pycache__ -arv ../usr "$B_PATH"

cd dist
dpkg-deb --build TVDemon
mv TVDemon.deb TVDemon-$VER.deb

rm -R TVDemon
