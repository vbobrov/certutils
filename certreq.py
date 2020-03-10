#!/usr/bin/python3
import ipaddress
import logging
import json
import sys
import argparse
import re
import tempfile
import os

def validip(ip):
	try:
		ipaddress.ip_address(ip)
	except ValueError:
		return(False)
	return(True)

def validemail(email):
    return(re.search(r'^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$',email))

def validdns(hostname):
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))

certattr={
	"cn":{
		"fullname":"commonName",
		"prompt":"Common Name (CN)",
		"multival":0
	},
	"e":{
		"fullname":"emailAddress",
		"prompt":"Email (E)",
		"multival":0
	},
	"ou":{
		"fullname":"organizationalUnitName",
		"prompt":"Organizational Unit (OU)",
		"multival":1
	},
	"dc":{
		"fullname":"domainComponent",
		"prompt":"Domain Component (DC)",
		"multival":1
	},
	"o":{
		"fullname":"organizationName",
		"prompt":"Organization (O)",
		"multival":0
	},
	"l":{
		"fullname":"localityName",
		"prompt":"Locality (L)",
		"multival":0
	},
	"s":{
		"fullname":"stateOrProvinceName",
		"prompt":"State (ST)",
		"multival":0
	},
	"c":{
		"fullname":"countryName",
		"prompt":"Country (C)",
		"multival":0
	},
	"san":{
		"fullname":"subjectAltName",
		"prompt":"Subject Alt Name (FQDN, IP or UPN). Comma Separated",
		"multival":0
	}
}
parser=argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,allow_abbrev=False,description="Certificate Request Tool")
for attr in certattr:
	if certattr[attr]["multival"]:
		parser.add_argument("-"+attr,help=certattr[attr]["prompt"]+". Multiple Allowed",default=[],action="append",metavar=certattr[attr]["fullname"])
	else:
		parser.add_argument("-"+attr,help=certattr[attr]["prompt"],default='',metavar=certattr[attr]["fullname"])
parser.add_argument("-dn",metavar="subjectName",help="Full Subject Line. Individual subject options ignored",default='')
keygroup=parser.add_mutually_exclusive_group(required=True)
keygroup.add_argument("-n",help="Generate new RSA private key in file specified",nargs=2,metavar=("keyfile","keysize"))
keygroup.add_argument("-k",help="Use existing RSA private in file specified",metavar="keyfile")
parser.add_argument("-w",help="Name of CSR file to output. STDOUT if omitted",metavar="csrfile")
parser.add_argument("-m",help="Display instructions to manually create the request",action="store_true")
parser.add_argument("-v",help="Display more details",action="store_true")
args=parser.parse_args()
arglist=vars(args)
logFormatter='%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(format=logFormatter, level=logging.DEBUG if args.v else logging.ERROR)
logger=logging.getLogger(__name__)
fullsubject=arglist["dn"]
if fullsubject:
	logger.debug("Full Subject: %s"%fullsubject)
	for rdn in fullsubject.split(","):
		rdn=re.sub(r"^\s+|\s+$","",rdn)
		(attrname,attrval)=rdn.split("=")
		validattr=0
		for attr in certattr:
			if attr=="san":
				continue
			if attrname.lower()==attr.lower():
				validattr=1
				if certattr[attr]["multival"]:
					if not arglist[attr]:
						arglist[attr]=[]
					arglist[attr].append(attrval)
				else:
					arglist[attr]=attrval
				break
		if not validattr:
			logger.error("Invalid RDN: %s"%rdn)
			sys.exit()
subject=''
while not subject:
	for attr in certattr:
		if attr=="san":
			continue
		attrval=arglist[attr]
		logger.debug("%s: %s"%(attr,attrval))
		if attrval:
			if certattr[attr]["multival"]:
				for multiattr in attrval:
					subject+=attr+"="+multiattr+","
			else:
				subject+=attr+"="+attrval+","
	if not subject:
		logger.info("No subject supplied in CLI. Collecting Interactively")
		print("Please enter information about the request.")
		print("Empty string to skip the value")
		for attr in certattr:
			attrprompt=certattr[attr]["prompt"]
			if certattr[attr]["multival"]:
				attrprompt+=". Multiple values comma separated"
			attrprompt+=": "
			attrval=input(attrprompt)
			attrval=re.sub(r"^\s+|\s+$","",attrval)
			if attrval:
				if certattr[attr]["multival"]:
					arglist[attr]=[]
					for attrval1 in attrval.split(","):
						attrval1=re.sub(r"^\s+|\s+$","",attrval1)
						arglist[attr].append(attrval1)
				else:
					arglist[attr]=attrval
if arglist["san"]:
	logger.debug("Processing SAN: %s"%arglist["san"])
	sanip=[]
	sandns=[]
	sanupn=[]
	for san in arglist["san"].split(","):
		if validip(san):
			logger.debug("IP: %s"%san)
			sanip.append(san)
		elif validdns(san):
			logger.debug("DNS: %s"%san)
			sandns.append(san)
		elif validemail(san):
			logger.debug("UPN: %s"%san)
			sanupn.append(san)
		else:
			logger.error("Invalid SAN: %s"%san)
		
subject=re.sub(",$","",subject)
logger.info("Subject: "+subject)
sslcfg="""[ req ]
distinguished_name	= req_distinguished_name
string_mask = utf8only
prompt=no
req_extensions = v3_req

[ req_distinguished_name ]
"""
for attr in certattr:
	if arglist[attr]:
		if attr=="san":
			continue
		if certattr[attr]["multival"]:
			attridx=0
			for attrval1 in arglist[attr]:
				sslcfg+="%d.%s=%s\n"%(attridx,certattr[attr]["fullname"],attrval1)
				attridx+=1
		else:
			sslcfg+="%s=%s\n"%(certattr[attr]["fullname"],arglist[attr])
sslcfg+="""
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names
extendedKeyUsage=serverAuth,clientAuth

[ alt_names ]
"""
sanidx=1
for san in sandns:
	sslcfg+="DNS.%d=%s\n"%(sanidx,san)
	sanidx+=1
sanidx=1
for san in sanip:
	sslcfg+="IP.%d=%s\n"%(sanidx,san)
	sanidx+=1
sanidx=1
for san in sanupn:
	sslcfg+="otherName.%d=1.3.6.1.4.1.311.20.2.3;UTF8:%s\n"%(sanidx,san)
	sanidx+=1
logger.debug("Genrated OpenSSL Config:\n"+sslcfg)
cfgfilename=tempfile.NamedTemporaryFile(prefix="openssl",suffix=".cfg")
if arglist["m"]:
	cfgfilename.name="openssl.cfg"
else:
	cfgfile=open(cfgfilename.name,"w")
	cfgfile.write(sslcfg)
	cfgfile.close()
	logger.debug("Wrote OpenSSL Config to "+cfgfilename.name)
if arglist["n"]:
	sslcmd="openssl req -text -config %s -keyout %s -newkey %s -new"%(cfgfilename.name,arglist["n"][0],arglist["n"][1])
else:
	sslcmd="openssl req -text -config %s -key %s -new"%(cfgfilename.name,arglist["k"])
if arglist["w"]:
	sslcmd+=" -out %s"%arglist["csrfile"]
if arglist["m"]:
	print("""
1. Create openssl.cfg file with the following content
$ cat > openssl.cfg <<EOT
%s
EOT

2. Execute the following command
$ %s"""%(sslcfg,sslcmd))
else:
	logger.debug("Executing: "+sslcmd)
	os.system(sslcmd)
