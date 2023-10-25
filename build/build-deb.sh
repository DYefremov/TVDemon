#!/bin/bash
VER="1.3.0-Beta"
B_PATH="dist/TVDemon"

mkdir -p $B_PATH
cp -TRv debian "$B_PATH/DEBIAN"
rsync --exclude=__pycache__ -arv ../usr "$B_PATH"

cd dist
dpkg-deb --build TVDemon
mv TVDemon.deb TVDemon-$VER.deb

rm -R TVDemon
