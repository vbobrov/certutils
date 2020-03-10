# certutils

These tools are wrappers for common openssl operations. 

## Usage - certreq.py

This tool simplifies generation of Certificate Signing Requests (CSR).
The contents of the CSR can be supplied via CLI options and also collected interactively.

CLI Options:

```
usage: certreq.py [-h] [-cn commonName] [-e emailAddress]
                  [-ou organizationalUnitName] [-dc domainComponent]
                  [-o organizationName] [-l localityName]
                  [-s stateOrProvinceName] [-c countryName]
                  [-san subjectAltName] [-dn subjectName]
                  (-n keyfile keysize | -k keyfile) [-w csrfile] [-m] [-v]

Certificate Request Tool

optional arguments:
  -h, --help            show this help message and exit
  -cn commonName        Common Name (CN)
  -e emailAddress       Email (E)
  -ou organizationalUnitName
                        Organizational Unit (OU). Multiple Allowed
  -dc domainComponent   Domain Component (DC). Multiple Allowed
  -o organizationName   Organization (O)
  -l localityName       Locality (L)
  -s stateOrProvinceName
                        State (ST)
  -c countryName        Country (C)
  -san subjectAltName   Subject Alt Name (FQDN, IP or UPN). Comma Separated
  -dn subjectName       Full Subject Line. Individual subject options ignored
  -n keyfile keysize    Generate new RSA private key in file specified
  -k keyfile            Use existing RSA private in file specified
  -w csrfile            Name of CSR file to output. STDOUT if omitted
  -m                    Display instructions to manually create the request
  -v                    Display more details
````

Example 1 - Generate a new key and a new CSR interactively

```
$ ./certreq.py -n key1.pem 2048
Please enter information about the request.
Empty string to skip the value
Common Name (CN): www.example.com
Email (E): admin@example.com
Organizational Unit (OU). Multiple values comma separated: External,WWW
Domain Component (DC). Multiple values comma separated: 
Organization (O): Example Co
Locality (L): New York
State (ST): NY
Country (C): US 
Subject Alt Name (FQDN, IP or UPN). Comma Separated: www.example.com,apps.example.com
Generating a 2048 bit RSA private key
.......................+++
........................................+++
writing new private key to 'key1.pem'
Enter PEM pass phrase:
Verifying - Enter PEM pass phrase:
-----
-----BEGIN CERTIFICATE REQUEST-----
MIIDWzCCAkMCAQAwgZ8xGDAWBgNVBAMMD3d3dy5leGFtcGxlLmNvbTEgMB4GCSqG
------------------------------- snip ---------------------------
9sYcQhDQNxSuZ6OTDA04UV4d6COBkAAOI7kTwmum/NOSTxF968+IxWk8Uo/vsfw=
-----END CERTIFICATE REQUEST-----
```

Example 2 - Generate a CSR from command line using an existing key

```
$ ./certreq.py -k key1.pem -cn www.example.com -e 'admin@example.com' -o 'Example Co' -l 'New York' -s NY -c US -san www.example.com,apps.example.com -ou External -ou WWW

Enter pass phrase for key1.pem:
-----BEGIN CERTIFICATE REQUEST-----
MIIDWzCCAkMCAQAwgZ8xGDAWBgNVBAMMD3d3dy5leGFtcGxlLmNvbTEgMB4GCSqG
------------------------------- snip ---------------------------
i/hybsQTG9hTtX5kWnqml+x95Zyy/s4Y+C5eyvq0mN/Wkh3C1FDFzZYiW3RRfpU=
-----END CERTIFICATE REQUEST-----
```

Example 3 - Print instructions on manually generating the CSR manually

```
$ ./certreq.py -m -k key1.pem -cn www.example.com -e 'admin@example.com' -o 'Example Co' -l 'New York' -s NY -c US -san www.example.com,apps.example.com -ou External -ou WWW

1. Create openssl.cfg file with the following content
$ cat > openssl.cfg
[ req ]
distinguished_name      = req_distinguished_name
string_mask = utf8only
prompt=no
req_extensions = v3_req

[ req_distinguished_name ]
commonName=www.example.com
emailAddress=admin@example.com
0.organizationalUnitName=External
1.organizationalUnitName=WWW
organizationName=Example Co
localityName=New York
stateOrProvinceName=NY
countryName=US

[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names
extendedKeyUsage=serverAuth,clientAuth

[ alt_names ]
DNS.1=www.example.com
DNS.2=apps.example.com


2. Execute the following command
$ openssl req -text -config openssl.cfg -key key1.pem -new
```