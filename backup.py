#!/usr/bin/python

import datetime
import os
import string
import tarfile

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from datetime import timedelta

# Configuration

dir_backup = '/tmp/pbackup/'

aws_access_key = 'login'
aws_secret_key = 'key'
aws_bucket = 'backup-name'

aes_password = 'AesPassword'

mysql_hostname = '127.0.0.1'
mysql_username = 'root'
mysql_password = ''
mysql_dump_path = '/usr/bin/mysqldump'

openssl_path = '/usr/bin/openssl'

dirs = [
        '/home/git/',
	'/etc/'
        ]
		
dbs = [
        'database1',
        'database2',
        ]

# Script Configuration
today = datetime.date.today()
previous = today - timedelta(days = 7)

from os.path import normpath, basename

# File Backups
for d in dirs:

    file = basename(normpath(d))

    print '[FILE] Creating archive for ' + file
    
    tar_name = file + '-' + str(today) + '.files.tar.gz'
    
    tar = tarfile.open(os.path.join(dir_backup, tar_name), 'w:gz')
    tar.add(d)
    tar.close()
    
    print '[FILE] Encrypting archive for ' + file
    
    os.popen(openssl_path + " aes-256-cbc -pass pass:%s -salt -in %s -out %s.aes" % (aes_password, os.path.join(dir_backup, tar_name), os.path.join(dir_backup, tar_name)))
    
    os.remove(os.path.join(dir_backup, tar_name));
             
# MySQL Backups
for d in dbs:

    d = d.strip()
    file = dir_backup + "%s-%s.sql" % (d, today)

    print '[DB] Creating archive for ' + file

    os.popen(mysql_dump_path + " -u %s -p%s -h %s -e --opt -c %s | gzip -c > %s.gz" % (mysql_username, mysql_password, mysql_hostname, d, file))
    
    file = file + ".gz"
    
    print '[FILE] Encrypting archive for ' + file
    
    os.popen(openssl_path + " aes-256-cbc -pass pass:%s -salt -in %s -out %s.aes" % (aes_password, file, file))
    
    os.remove(file);

# Establish S3 Connection
s3 = S3Connection(aws_access_key, aws_secret_key, host="sds.tiktalik.com", is_secure=False)
#b = s3.get_bucket(aws_bucket)

from boto.s3.bucket import Bucket

b = Bucket(s3, aws_bucket)

# Send files to S3
for f in dirs:

    file = basename(normpath(f)) + '-' + str(today) + '.files.tar.gz.aes'

    print '[S3] Uploading file archive ' + file + '...'

    k = Key(b)
    k.key = file
    k.set_contents_from_filename(dir_backup + file, policy="public-read")

    os.remove(dir_backup + file);

    print '[S3] Clearing previous file archive ' + file + '...'

    # Conserve monthly backups (Previous Month)
    if previous != str(datetime.datetime.today().year) + '-' + str(datetime.datetime.today().day) + '-3':
        # Clean up files on S3
        k = Key(b)
        k.key = basename(normpath(f)) + '-' + str(previous) + '.files.tar.gz.aes'
        b.delete_key(k)
	
# Send DBs to S3
for d in dbs:

    d = d.strip()
    file = "%s-%s.sql.gz.aes" % (d, today)

    print '[S3] Uploading database dump ' + file + '...'

    k = Key(b)
    k.key = file
    k.set_contents_from_filename(dir_backup + file, policy="public-read")
#    k.set_acl("public-read")

    os.remove(dir_backup + file);

    print '[S3] Clearing previous database dump ' + file + '...'

    # Conserve backups 
    if previous != str(datetime.datetime.today().year) + '-' + str(datetime.datetime.today().day) + '-3':
        # Clean up files on S3
        k = Key(b)
        k.key = "%s-%s.sql.gz.aes" % (d, previous)
        b.delete_key(k)
