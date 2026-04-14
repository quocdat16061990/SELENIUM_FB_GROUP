#!/bin/bash
# Kịch bản helper tự động nhúng 1 file python vào crontab có sẵn biến môi trường

if [ "$#" -ne 2 ]; then
    echo "Sử dụng: bash $0 <số-phút-lặp> <ten_file.py>"
    exit 1
fi

PHUT_LAP=$1
FILE_PY=$2
CUR_DIR=$PWD

# Biểu thức cron
CRON_EXP="*/$PHUT_LAP * * * *"
# Lệnh thực thi đi kèm bảo kê UI X11
CMD="export DISPLAY=:10.0 && export XAUTHORITY=/home/ubuntu/.Xauthority && cd $CUR_DIR && $CUR_DIR/venv/bin/python $FILE_PY >> $CUR_DIR/cron_bot.log 2>&1"

# Cài đặt qua dạng nối cron
(crontab -l 2>/dev/null; echo "$CRON_EXP $CMD") | crontab -
echo "Đã thêm lệnh sau vào Crontab cấu hình $PHUT_LAP phút / lần:"
echo "$CRON_EXP $CMD"
