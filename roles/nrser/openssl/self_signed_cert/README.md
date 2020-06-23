Generate Self-Signed SSL Certificate With OpenSSL
==============================================================================

This role will use `openssl req` to generate a self-signed SSL certificate,
which are useful for connecting to intranet services over HTTPS.

Usage
------------------------------------------------------------------------------


Trusting Certificates
------------------------------------------------------------------------------

Copy the certificate (`.crt` file) to your local machine, then follow the
platform and application-specific instructions below.

### MacOS ###

Open _KeyChain Access_ and drag the `.crt` file to the dock icon, which will 
open a prompt to add the cert. I chose the `System` key-chain.

After adding, find the certificate in the _Certificates_ category, double click,
and under _Trust_ set at least the SSL one to _Always Trust_ (for HTTPS). Close
dialog to confirm.

### Firefox ###

> As of Firefox `77.0.1` (64 bit)

Does not trust certificates just because the system does :/ So there are some 
additional steps, which I got from:

<https://support.mozilla.org/en-US/kb/setting-certificate-authorities-firefox>

1.  Move or copy the `.crt` file to
    
        ~/Library/Application Support/Mozilla/Certificates
    
    You may need to create that directory.
    
2.  Browse to `about:config` in Firefox and set
    
        security.enterprise_roots.enabled
    
    to `true`.

What's listed there worked... once. Then it stopped. So, after much search n'
sift, this is what I got:

1.  Browse to <about:preferences#privacy>
    
2.  Scroll all the way down to _Certificates_ and click _View Certificates_
    button on the right side.
    
3.  On the _Authorities_ tab click _Import.._
    
4.  Import the `.crt` file
    
5.  I selected to trust it for sites and emails.
    
6.  Restart Firefox (maybe needed?)
