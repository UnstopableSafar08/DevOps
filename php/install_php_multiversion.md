# Multi-Version PHP Installation on EL9
## Using Remi Repository — PHP 7.2, 8.1, 8.2, 8.3

> **Target OS:** RHEL 9 / AlmaLinux 9 / Rocky Linux 9 (EL9)  
> **Repository:** [Remi's RPM Repository](https://rpms.remirepo.net/)  
> **Versions:** PHP 7.2, 8.1, 8.2, 8.3 (side-by-side)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Module Mapping & Missing Modules Analysis](#module-mapping--missing-modules-analysis)
3. [PHP 7.2 Installation](#php-72-installation)
4. [PHP 8.1 Installation](#php-81-installation)
5. [PHP 8.2 Installation](#php-82-installation)
6. [PHP 8.3 Installation](#php-83-installation)
7. [Post-Installation](#post-installation)
8. [FPM Service Management](#fpm-service-management)
9. [Quick Reference Paths](#quick-reference-paths)

---

## Prerequisites

```bash
# 1. Install EPEL
sudo dnf install -y epel-release

# 2. Install Remi repository for EL9
sudo dnf install -y https://rpms.remirepo.net/enterprise/remi-release-9.rpm

# 3. Import GPG key
sudo rpm --import https://rpms.remirepo.net/RPM-GPG-KEY-remi2018

# 4. Enable CRB (CodeReady Builder) — required by some Remi dependencies
sudo dnf config-manager --set-enabled crb

# 5. Install dnf-utils and refresh cache
sudo dnf install -y dnf-utils
sudo dnf makecache -y
```

---

## Module Mapping & Missing Modules Analysis

### Added Modules (Missing from original list)

The following were **missing** from the original module/package list and have been added:

| Module/Package | Why Added |
|---|---|
| `php-cli` | Essential PHP command-line binary |
| `php-common` | Core built-ins: `Core`, `ctype`, `date`, `filter`, `hash`, `json`, `openssl`, `pcre`, `Reflection`, `session`, `SPL`, `standard`, `tokenizer` |
| `php-fpm` | FastCGI Process Manager for web serving |
| `php-bcmath` | `bcmath` — arbitrary precision math |
| `php-dba` | Database abstraction layer |
| `php-devel` | Header files for compiling PECL extensions |
| `php-process` | **Consolidates**: `pcntl`, `shmop`, `sysvmsg`, `sysvsem`, `sysvshm` |
| `php-ftp` | `ftp` module (was in phpinfo list, missing from dnf command) |
| `php-zip` | `zip` module (was in phpinfo list, missing from dnf command) |

### Package Consolidation (1 package → multiple modules)

| Remi Package | PHP Modules Provided |
|---|---|
| `php{ver}-php-common` | `Core`, `ctype`, `date`, `fileinfo`, `filter`, `gettext`, `hash`, `iconv`(8.x), `json`, `openssl`, `pcre`, `posix`, `Reflection`, `session`, `SPL`, `standard`, `tokenizer`, `zlib`(8.x) |
| `php{ver}-php-mysqlnd` | `mysqli`, `mysqlnd`, `pdo_mysql` |
| `php{ver}-php-xml` | `dom`, `libxml`, `SimpleXML`, `xml`, `xmlreader`, `xmlwriter`, `xsl`, `wddx`(7.2 only) |
| `php{ver}-php-sqlite3` | `sqlite3`, `pdo_sqlite` |
| `php{ver}-php-process` | `pcntl`, `shmop`, `sysvmsg`, `sysvsem`, `sysvshm` |
| `php{ver}-php-pdo` | `PDO` base driver |
| `php{ver}-php-opcache` | `Zend OPcache` |

### Version-Specific Module Differences

| Module | PHP 7.2 | PHP 8.1 | PHP 8.2 | PHP 8.3 |
|---|:---:|:---:|:---:|:---:|
| `wddx` | ✅ (in `php-xml`) | ❌ Removed | ❌ Removed | ❌ Removed |
| `xmlrpc` | ✅ `php-xmlrpc` (bundled) | ✅ `pecl-xmlrpc` | ✅ `pecl-xmlrpc` | ✅ `pecl-xmlrpc` |
| `iconv` | ✅ standalone `php-iconv` | ✅ in `php-common` | ✅ in `php-common` | ✅ in `php-common` |
| `zlib` | ✅ standalone `php-zlib` | ✅ in `php-common` | ✅ in `php-common` | ✅ in `php-common` |
| `bcmath` | ✅ | ✅ | ✅ | ✅ |

---

## PHP 7.2 Installation

```bash
sudo dnf install -y \
  php72 \
  php72-php-cli \
  php72-php-common \
  php72-php-fpm \
  php72-php-bcmath \
  php72-php-bz2 \
  php72-php-calendar \
  php72-php-curl \
  php72-php-dba \
  php72-php-devel \
  php72-php-exif \
  php72-php-ftp \
  php72-php-gd \
  php72-php-gettext \
  php72-php-iconv \
  php72-php-mbstring \
  php72-php-mysqlnd \
  php72-php-opcache \
  php72-php-pdo \
  php72-php-process \
  php72-php-readline \
  php72-php-soap \
  php72-php-sockets \
  php72-php-sqlite3 \
  php72-php-xml \
  php72-php-xmlrpc \
  php72-php-zip \
  php72-php-zlib \
  php72-php-pecl-igbinary \
  php72-php-pecl-msgpack \
  php72-php-pecl-redis
```

**Full module coverage for PHP 7.2:**

| Package | Modules Covered |
|---|---|
| `php72-php-common` | `Core`, `ctype`, `date`, `fileinfo`, `filter`, `hash`, `json`, `openssl`, `pcre`, `posix`, `Reflection`, `session`, `SPL`, `standard`, `tokenizer` |
| `php72-php-bcmath` | `bcmath` |
| `php72-php-bz2` | `bz2` |
| `php72-php-calendar` | `calendar` |
| `php72-php-curl` | `curl` |
| `php72-php-exif` | `exif` |
| `php72-php-ftp` | `ftp` |
| `php72-php-gd` | `gd` |
| `php72-php-gettext` | `gettext` |
| `php72-php-iconv` | `iconv` |
| `php72-php-mbstring` | `mbstring` |
| `php72-php-mysqlnd` | `mysqli`, `mysqlnd`, `pdo_mysql` |
| `php72-php-opcache` | `Zend OPcache` |
| `php72-php-pdo` | `PDO` |
| `php72-php-process` | `pcntl`, `shmop`, `sysvmsg`, `sysvsem`, `sysvshm` |
| `php72-php-readline` | `readline` |
| `php72-php-soap` | `soap` |
| `php72-php-sockets` | `sockets` |
| `php72-php-sqlite3` | `sqlite3`, `pdo_sqlite` |
| `php72-php-xml` | `dom`, `libxml`, `SimpleXML`, `xml`, `xmlreader`, `xmlwriter`, `xsl`, **`wddx`** |
| `php72-php-xmlrpc` | `xmlrpc` |
| `php72-php-zip` | `zip` |
| `php72-php-zlib` | `zlib` |
| `php72-php-pecl-igbinary` | `igbinary` |
| `php72-php-pecl-msgpack` | `msgpack` |
| `php72-php-pecl-redis` | `redis` |

---

## PHP 8.1 Installation

```bash
sudo dnf install -y \
  php81 \
  php81-php-cli \
  php81-php-common \
  php81-php-fpm \
  php81-php-bcmath \
  php81-php-bz2 \
  php81-php-calendar \
  php81-php-curl \
  php81-php-dba \
  php81-php-devel \
  php81-php-exif \
  php81-php-ftp \
  php81-php-gd \
  php81-php-gettext \
  php81-php-mbstring \
  php81-php-mysqlnd \
  php81-php-opcache \
  php81-php-pdo \
  php81-php-process \
  php81-php-readline \
  php81-php-soap \
  php81-php-sockets \
  php81-php-sqlite3 \
  php81-php-xml \
  php81-php-pecl-xmlrpc \
  php81-php-zip \
  php81-php-pecl-igbinary \
  php81-php-pecl-msgpack \
  php81-php-pecl-redis
```

> ⚠️ **`wddx` removed in PHP 8.0** — no longer available  
> ⚠️ **`xmlrpc` moved to PECL** — use `php81-php-pecl-xmlrpc`

---

## PHP 8.2 Installation

```bash
sudo dnf install -y \
  php82 \
  php82-php-cli \
  php82-php-common \
  php82-php-fpm \
  php82-php-bcmath \
  php82-php-bz2 \
  php82-php-calendar \
  php82-php-curl \
  php82-php-dba \
  php82-php-devel \
  php82-php-exif \
  php82-php-ftp \
  php82-php-gd \
  php82-php-gettext \
  php82-php-mbstring \
  php82-php-mysqlnd \
  php82-php-opcache \
  php82-php-pdo \
  php82-php-process \
  php82-php-readline \
  php82-php-soap \
  php82-php-sockets \
  php82-php-sqlite3 \
  php82-php-xml \
  php82-php-pecl-xmlrpc \
  php82-php-zip \
  php82-php-pecl-igbinary \
  php82-php-pecl-msgpack \
  php82-php-pecl-redis
```

> ⚠️ **`wddx` removed in PHP 8.0** — no longer available  
> ⚠️ **`xmlrpc` moved to PECL** — use `php82-php-pecl-xmlrpc`

---

## PHP 8.3 Installation

```bash
sudo dnf install -y \
  php83 \
  php83-php-cli \
  php83-php-common \
  php83-php-fpm \
  php83-php-bcmath \
  php83-php-bz2 \
  php83-php-calendar \
  php83-php-curl \
  php83-php-dba \
  php83-php-devel \
  php83-php-exif \
  php83-php-ftp \
  php83-php-gd \
  php83-php-gettext \
  php83-php-mbstring \
  php83-php-mysqlnd \
  php83-php-opcache \
  php83-php-pdo \
  php83-php-process \
  php83-php-readline \
  php83-php-soap \
  php83-php-sockets \
  php83-php-sqlite3 \
  php83-php-xml \
  php83-php-pecl-xmlrpc \
  php83-php-zip \
  php83-php-pecl-igbinary \
  php83-php-pecl-msgpack \
  php83-php-pecl-redis
```

> ⚠️ **`wddx` removed in PHP 8.0** — no longer available  
> ⚠️ **`xmlrpc` moved to PECL** — use `php83-php-pecl-xmlrpc`

---

## Post-Installation

### Verify all versions

```bash
php72 -v && php72 -m | sort
php81 -v && php81 -m | sort
php82 -v && php82 -m | sort
php83 -v && php83 -m | sort
```

### Verify specific module is loaded

```bash
# Check a module across all versions at once
for v in 72 81 82 83; do
  echo "--- PHP $v ---"
  php${v} -m | grep -iE 'redis|igbinary|msgpack|opcache'
done
```

---

## FPM Service Management

Each PHP version runs its own independent FPM service and listens on a separate socket/port.

```bash
# Enable and start all FPM services
sudo systemctl enable --now php72-php-fpm
sudo systemctl enable --now php81-php-fpm
sudo systemctl enable --now php82-php-fpm
sudo systemctl enable --now php83-php-fpm

# Check status
sudo systemctl status php72-php-fpm
sudo systemctl status php81-php-fpm
sudo systemctl status php82-php-fpm
sudo systemctl status php83-php-fpm

# Restart a specific version
sudo systemctl restart php83-php-fpm
```

### Recommended: Separate Unix sockets per version

Edit `/etc/opt/remi/php{ver}/php-fpm.d/www.conf` and set:

```ini
; PHP 7.2
listen = /run/php72-fpm.sock

; PHP 8.1
listen = /run/php81-fpm.sock

; PHP 8.2
listen = /run/php82-fpm.sock

; PHP 8.3
listen = /run/php83-fpm.sock
```

---

## Quick Reference Paths

| Version | Binary | php.ini | FPM config dir | FPM socket |
|---|---|---|---|---|
| 7.2 | `/usr/bin/php72` | `/etc/opt/remi/php72/php.ini` | `/etc/opt/remi/php72/php-fpm.d/` | `/run/php72-fpm.sock` |
| 8.1 | `/usr/bin/php81` | `/etc/opt/remi/php81/php.ini` | `/etc/opt/remi/php81/php-fpm.d/` | `/run/php81-fpm.sock` |
| 8.2 | `/usr/bin/php82` | `/etc/opt/remi/php82/php.ini` | `/etc/opt/remi/php82/php-fpm.d/` | `/run/php82-fpm.sock` |
| 8.3 | `/usr/bin/php83` | `/etc/opt/remi/php83/php.ini` | `/etc/opt/remi/php83/php-fpm.d/` | `/run/php83-fpm.sock` |

### Extension config dirs (drop-in `.ini` files)

```
/etc/opt/remi/php72/php.d/
/etc/opt/remi/php81/php.d/
/etc/opt/remi/php82/php.d/
/etc/opt/remi/php83/php.d/
```

---

## All-in-One Script

Use `install_php_all.sh` to set up the Remi repo and install all 4 versions in one run:

```bash
sudo bash install_php_all.sh
```

Or install versions individually:

```bash
sudo bash install_php72.sh
sudo bash install_php81.sh
sudo bash install_php82.sh
sudo bash install_php83.sh
```

---

*Generated for EL9 — RHEL / AlmaLinux / Rocky Linux 9*
