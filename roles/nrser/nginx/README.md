`nrser/nginx` Role -- Install & Configure Nginx
==============================================================================

Use it something like this:

```yaml
vars:
  nginx_sites:
    - name: example.com
      server_name: example.com
      root: /var/www/example.com
      http_template: example.com.http.conf
      https: false

roles:
  - role: nrser/nginx

```
