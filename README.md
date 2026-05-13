# Databricks Auto-Login

Tool otomatis untuk login ke Databricks menggunakan autentikasi Microsoft Azure AD (Microsoft Entra ID) melalui MSAL (Microsoft Authentication Library).

## Deskripsi

Proyek ini menyediakan tool CLI untuk melakukan autentikasi otomatis ke workspace Databricks menggunakan Azure AD. Mendukung dua metode login:

1. **Service Principal** - Menggunakan client credentials (tanpa interaksi user)
2. **Interactive Login** - Membuka browser untuk login dengan akun Microsoft

Fitur utama:
- Token caching untuk menghindari login berulang
- Dukungan silent login (menggunakan token yang tersimpan)
- Test koneksi ke Databricks API
- Pesan bilingual (Indonesia/Inggris)

## Prasyarat

### Registrasi Aplikasi di Azure AD

1. Buka [Azure Portal](https://portal.azure.com) > Azure Active Directory > App Registrations
2. Klik "New registration"
3. Isi nama aplikasi (misal: "Databricks Auto-Login")
4. Pilih "Accounts in this organizational directory only" untuk Supported account types
5. Set Redirect URI ke `http://localhost:8400` (Web)
6. Klik "Register"

Setelah aplikasi terdaftar:

1. Catat **Application (client) ID** dan **Directory (tenant) ID**
2. Untuk Service Principal: Buka "Certificates & secrets" > "New client secret" > Catat secret value
3. Buka "API permissions" > "Add a permission" > "APIs my organization uses"
4. Cari "AzureDatabricks" (ID: 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d)
5. Pilih "user_impersonation" permission
6. Klik "Grant admin consent" (memerlukan akses admin)

### Konfigurasi Databricks Workspace

1. Buka Databricks workspace > Admin Console > Service Principals
2. Tambahkan Service Principal dengan Application ID yang sudah didaftarkan
3. Berikan akses yang sesuai (workspace access, cluster access, dll)

## Instalasi

```bash
# Clone repository
git clone <repository-url>

# Install dependencies
pip install -r requirements.txt
```

## Konfigurasi

1. Salin file template konfigurasi:

```bash
cp config.example.json config.json
```

2. Edit `config.json` dengan nilai yang sesuai:

```json
{
    "tenant_id": "azure-tenant-id-anda",
    "client_id": "azure-app-client-id-anda",
    "client_secret": "client-secret-untuk-service-principal",
    "databricks_host": "https://adb-xxxxxxxxxxxx.xx.azuredatabricks.net",
    "databricks_scope": "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default",
    "redirect_uri": "http://localhost:8400",
    "token_cache_file": ".token_cache.json"
}
```

### Penjelasan Field

| Field | Wajib | Deskripsi |
|-------|-------|-----------|
| `tenant_id` | Ya | Azure AD Tenant ID |
| `client_id` | Ya | Application (Client) ID dari App Registration |
| `client_secret` | Tidak* | Client Secret (wajib untuk Service Principal) |
| `databricks_host` | Ya | URL workspace Databricks |
| `databricks_scope` | Tidak | Azure Databricks resource scope (default sudah benar) |
| `redirect_uri` | Tidak | Redirect URI untuk interactive login (default: http://localhost:8400) |
| `token_cache_file` | Tidak | Lokasi file cache token (default: .token_cache.json) |

## Penggunaan

### Login Otomatis (Auto)

Mencoba silent login terlebih dahulu, jika gagal akan fallback ke interactive:

```bash
python3 -m databricks_auto_login.main login --method auto
```

### Login Interaktif

Membuka browser untuk autentikasi:

```bash
python3 -m databricks_auto_login.main login --method interactive
```

### Login Service Principal

Menggunakan client credentials (tanpa browser):

```bash
python3 -m databricks_auto_login.main login --method service_principal
```

### Cek Status Token

```bash
python3 -m databricks_auto_login.main status
```

### Test Koneksi

```bash
python3 -m databricks_auto_login.main test-connection
```

## Troubleshooting

### Error: "AADSTS7000215: Invalid client secret"

- Pastikan `client_secret` di config.json masih valid
- Client secret memiliki masa berlaku, buat yang baru jika sudah expired

### Error: "AADSTS50011: Reply URL does not match"

- Pastikan `redirect_uri` di config.json sama dengan yang terdaftar di Azure Portal
- Default: `http://localhost:8400`

### Error: "Connection failed" saat test-connection

- Pastikan `databricks_host` benar dan bisa diakses
- Pastikan Service Principal memiliki akses ke workspace

### Error: "No valid token available"

- Jalankan perintah `login` terlebih dahulu
- Token mungkin sudah expired, login ulang

---

## English Section

### Overview

This tool provides automated login to Databricks workspaces using Microsoft Azure AD (Entra ID) authentication via MSAL. It supports both service principal (client credentials) and interactive browser-based login flows with token caching.

### Quick Start

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `config.example.json` to `config.json` and fill in your Azure AD and Databricks details
3. Run: `python3 -m databricks_auto_login.main login --method auto`

### Commands

- `login --method auto|interactive|service_principal` - Authenticate to Databricks
- `status` - Check if a valid token exists
- `test-connection` - Verify Databricks API connectivity

### License

MIT
