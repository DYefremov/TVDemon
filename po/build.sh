#!/bin/bash
for f in *.po;
do
  msgfmt $f -o ../usr/share/locale/${f:8:2}/LC_MESSAGES/tvdemon.mo
done
