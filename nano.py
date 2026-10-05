import logging
import random
import string
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==============================================================================
# OWNER & BOT CONFIGURATION
# ==============================================================================
TOKEN_BOT = "ISI_TOKEN_BOT_KAMU_DISINI"
ADMIN_USERNAME = "@UsernameAdminZayn"  # Ganti dengan username Telegram admin utama
ADMIN_ID = 123456789  # Ganti dengan ID Telegram Anda (angka) untuk panel admin
FEES_REKBER = 5000  # Biaya jasa rekber default (Flat)

# --- REKENING RESMI ADMIN ---
REKENING_ADMIN = (
    "🏦 **SEABANK:** `901488517664`\n"
    "👤 **Atas Nama:** Andrean Multajam"
)

# ==============================================================================
# DATABASE MANAGEMENT (SQLite)
# ==============================================================================
DB_NAME = "zayn_rekber.db"

def init_db():
    """Inisialisasi tabel database transaksi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaksi (
            trx_id TEXT PRIMARY KEY,
            buyer TEXT,
            seller TEXT,
            barang TEXT,
            harga INTEGER,
            fee INTEGER,
            total INTEGER,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_transaction(trx_id, buyer, seller, barang, harga, fee, total, status):
    """Menyimpan transaksi baru ke database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO transaksi VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
        (trx_id, buyer, seller, barang, harga, fee, total, status)
    )
    conn.commit()
    conn.close()

def get_transaction(trx_id):
    """Mengambil data detail transaksi berdasarkan ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transaksi WHERE trx_id = ?', (trx_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "trx_id": row[0], "buyer": row[1], "seller": row[2], 
            "barang": row[3], "harga": row[4], "fee": row[5], 
            "total": row[6], "status": row[7]
        }
    return None

def update_transaction_status(trx_id, status):
    """Memperbarui status transaksi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE transaksi SET status = ? WHERE trx_id = ?', (status, trx_id))
    conn.commit()
    conn.close()

def get_stats():
    """Mengambil ringkasan statistik transaksi sukses."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(total) FROM transaksi WHERE status = 'Sukses / Selesai'")
    row = cursor.fetchone()
    conn.close()
    total_sukses = row[0] if row and row[0] else 0
    total_perputaran = row[1] if row and row[1] else 0
    return total_sukses, total_perputaran

# Jalankan inisialisasi DB saat bot menyala
init_db()

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def generate_trx_id():
    """Membuat string acak sepanjang 6 karakter sebagai ID Transaksi."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ==============================================================================
# TELEGRAM USER HANDLERS
# ==============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan menu selamat datang bot Zayn Rekber."""
    user = update.effective_user
    welcome_text = (
        f"👋 Selamat datang di Bot Resmi **Zayn Rekber**!\n\n"
        f"Kami siap menjadi jembatan terpercaya untuk mengamankan transaksi jual-beli digital Anda.\n\n"
        f"📌 **Biaya Jasa:** Rp {FEES_REKBER:,} (Flat)\n"
        f"👑 **Owner/Admin:** {ADMIN_USERNAME}\n\n"
        f"Pilih menu di bawah ini atau ketik langsung perintahnya di grup:"
    )
    
    keyboard = [
        [InlineKeyboardButton("➕ Buat Transaksi Baru", callback_data="buat_trx")],
        [InlineKeyboardButton("📖 Panduan & Ketentuan", callback_data="panduan")],
        [InlineKeyboardButton("📊 Statistik Layanan", callback_data="statistik")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani setiap aksi penekanan tombol Inline Keyboard."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "buat_trx":
        text = (
            "📝 **Cara Membuat Transaksi di Zayn Rekber:**\n\n"
            "Silakan ketik perintah dengan format berikut di kolom chat bot atau grup Anda:\n"
            "`/rekber [Username_Penjual] [Nama_Barang] [Harga]`\n\n"
            "💡 *Catatan:* Gunakan tanda (`_`) sebagai pengganti spasi untuk nama barang.\n"
            "💡 *Contoh:* `/rekber @penjual_akun Akun_MLBB 150000`"
        )
        await query.message.reply_text(text, parse_mode="Markdown")
        
    elif query.data == "panduan":
        panduan_text = (
            "📖 **Alur Transaksi Zayn Rekber:**\n"
            "1. **Pembeli** membuat tagihan (*invoice*) menggunakan perintah `/rekber`.\n"
            "2. **Pembeli** mentransfer dana sesuai nominal total ke rekening SeaBank admin.\n"
            "3. Setelah admin mengonfirmasi dana masuk, **Penjual** dipersilakan menyerahkan barang/data kepada Pembeli.\n"
            "4. **Pembeli** melakukan pengecekan. Jika sudah aman, beri tahu admin untuk mencairkan dana ke Penjual.\n\n"
            "⚠️ **Peringatan:** Jangan menyerahkan data apa pun sebelum admin mengonfirmasi status dana aman!"
        )
        await query.message.reply_text(panduan_text, parse_mode="Markdown")
        
    elif query.data == "statistik":
        total_sukses, total_perputaran = get_stats()
        stats_text = (
            "📊 **STATISTIK LAYANAN ZAYN REKBER**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ **Transaksi Sukses:** {total_sukses} Transaksi\n"
            f"💰 **Total Dana Terproses:** Rp {total_perputaran:,}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Terima kasih telah memercayakan keamanan transaksi Anda kepada kami! 🙌"
        )
        await query.message.reply_text(stats_text, parse_mode="Markdown")

async def buat_rekber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Membuat dan menampilkan invoice transaksi rekber baru."""
    buyer = update.effective_user
    
    if len(context.args) < 3:
        await update.message.reply_text(
            "⚠️ **Format salah!** Gunakan:\n`/rekber [Username_Penjual] [Nama_Barang] [Harga]`", 
            parse_mode="Markdown"
        )
        return

    seller_username = context.args[0]
    nama_barang = context.args[1].replace("_", " ")
    
    try:
        harga = int(context.args[2])
    except ValueError:
        await update.message.reply_text("⚠️ **Harga harus berupa angka bulat saja (tanpa titik/koma)!**")
        return

    total_bayar = harga + FEES_REKBER
    trx_id = generate_trx_id()
    buyer_display = f"@{buyer.username}" if buyer.username else buyer.first_name

    # Simpan transaksi baru ke database SQLite
    save_transaction(
        trx_id, buyer_display, seller_username, nama_barang, 
        harga, FEES_REKBER, total_bayar, "Menunggu Pembayaran"
    )

    invoice_text = (
        f"🎫 **INVOICE ZAYN REKBER [ID: {trx_id}]**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 **Barang:** {nama_barang}\n"
        f"👤 **Pembeli:** {buyer_display}\n"
        f"🛍️ **Penjual:** {seller_username}\n"
        f"💰 **Harga:** Rp {harga:,}\n"
        f"⚙️ **Jasa Rekber:** Rp {FEES_REKBER:,}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 **TOTAL TRANSFER:** `Rp {total_bayar:,}`\n\n"
        f"📌 **Status:** ⏳ *Menunggu Pembayaran*\n\n"
        f"💳 **METODE PEMBAYARAN RESMI ADMIN:**\n"
        f"{REKENING_ADMIN}\n\n"
        f"⚠️ **Catatan:** Klik nomor rekening di atas untuk menyalin otomatis. Pastikan nominal transfer pas. "
        f"Jika sudah transfer, klik tombol kirim bukti di bawah ini."
    )

    keyboard = [
        [InlineKeyboardButton("✅ Hubungi Admin / Kirim Bukti", url=f"https://t.me/{ADMIN_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("❌ Batalkan Transaksi", callback_data=f"batal_{trx_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(invoice_text, parse_mode="Markdown", reply_markup=reply_markup)

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani pembatalan transaksi dari sisi pengguna sebelum diproses admin."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("batal_"):
        trx_id = query.data.split("_")[1]
        trx = get_transaction(trx_id)
        
        if trx:
            if trx['status'] == "Menunggu Pembayaran":
                update_transaction_status(trx_id, "Dibatalkan")
                await query.message.edit_text(
                    f"❌ **Transaksi {trx_id} di Zayn Rekber telah dibatalkan oleh pengguna.**", 
                    parse_mode="Markdown"
                )
            else:
                await query.message.reply_text("⚠️ **Transaksi ini tidak dapat dibatalkan karena status sudah diproses.**")
        else:
            await query.message.reply_text("⚠️ **Data transaksi tidak ditemukan.**")

async def status_layanan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan statistik layanan lewat command /stats."""
    total_sukses, total_perputaran = get_stats()
    stats_text = (
        "📊 **STATISTIK LAYANAN ZAYN REKBER**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ **Transaksi Sukses:** {total_sukses} Transaksi\n"
        f"💰 **Total Dana Terproses:** Rp {total_perputaran:,}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Terma kasih telah menggunakan jasa Zayn Rekber!"
    )
    await update.message.reply_text(stats_text, parse_mode="Markdown")

# ==============================================================================
# PANEL ADMIN COMMANDS
# ==============================================================================
async def admin_set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengubah status transaksi (Khusus Admin Zayn Rekber)."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ **Perintah ini hanya bisa digunakan oleh Admin utama Zayn Rekber!**")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ **Format salah!** Gunakan: `/status [ID_TRANSAKSI] [pembayaran_masuk/proses/selesai]`",
            parse_mode="Markdown"
        )
        return

    trx_id = context.args[0].upper()
    action = context.args[1].lower()

    trx = get_transaction(trx_id)
    if not trx:
        await update.message.reply_text("⚠️ **ID Transaksi tidak ditemukan di database.**")
        return

    if action == "pembayaran_masuk":
        new_status = "Dana Dipost (Aman)"
        status_msg = "✅ **Dana telah masuk ke Zayn Rekber!**\n📦 *Penjual silakan amankan & serahkan barang kepada Pembeli.*"
    elif action == "proses":
        new_status = "Sedang Dicek/Proses"
        status_msg = "🔄 **Transaksi sedang dalam proses pengecekan barang/akun oleh Pembeli.**"
    elif action == "selesai":
        new_status = "Sukses / Selesai"
        status_msg = "🎉 **Transaksi Selesai!**\n💵 *Dana telah diteruskan oleh Zayn Rekber ke pihak Penjual.*"
    else:
        await update.message.reply_text("⚠️ **Aksi tidak valid!** Gunakan: `pembayaran_masuk`, `proses`, atau `selesai`")
        return

    # Update data status di database
    update_transaction_status(trx_id, new_status)

    # Kirim notifikasi pembaruan status ke grup/chat
    update_text = (
        f"📢 **PEMBARUAN TRANSAKSI ZAYN REKBER [ID: {trx_id}]**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 **Barang:** {trx['barang']}\n"
        f"👤 **Pembeli:** {trx['buyer']}\n"
        f"🛍️ **Penjual:** {trx['seller']}\n"
        f"📌 **Status Terbaru:** 🏷️ **{new_status}**\n\n"
        f"{status_msg}"
    )
    await update.message.reply_text(update_text, parse_mode="Markdown")

# ==============================================================================
# MAIN BOOTSTRAPPER
# ==============================================================================
def main():
    """Fungsi utama untuk menjalankan Polling Bot."""
    print("Bot Zayn Rekber sedang berjalan...")
    app = Application.builder().token(TOKEN_BOT).build()

    # Registrasi Command & Callback Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rekber", buat_rekber))
    app.add_handler(CommandHandler("stats", status_layanan))
    app.add_handler(CommandHandler("status", admin_set_status))
    
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(buat_trx|panduan|statistik)$"))
    app.add_handler(CallbackQueryHandler(cancel_handler, pattern="^batal_"))

    # Memulai bot dengan mode polling
    app.run_polling()

if __name__ == "__main__":
    main()
