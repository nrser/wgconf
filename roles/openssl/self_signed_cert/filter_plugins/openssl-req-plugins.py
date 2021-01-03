def enc_value(value):
    if value is True:
        return 'yes'
    elif value is False:
        return 'no'
    else:
        return value

def fmt_domain(domain):
    return f"DNS:{domain}"

def fmt_domains(domains):
    if type(domains) is str:
        return fmt_domain(domains)
    
    return ",".join([fmt_domain(domain) for domain in domains])

class FilterModule:
    def filters(self):
        return dict(
            openssl_sscrt_enc_value=enc_value,
            openssl_sscrt_fmt_domains=fmt_domains,
        )
    