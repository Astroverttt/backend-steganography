import os
import base64
from PIL import Image


def text_to_binary(text: str) -> str:
    """Mengubah teks ke representasi biner 8-bit per karakter."""
    return ''.join(format(ord(char), '08b') for char in text)

def binary_to_text(binary: str) -> str:
    """Mengubah string biner kembali ke teks."""
    chars = []
    for i in range(0, len(binary), 8):
        byte = binary[i:i+8]
        if len(byte) == 8:
            chars.append(chr(int(byte, 2)))
    return ''.join(chars)

def xor_encrypt_decrypt(data: str, key: str) -> str:
    """Melakukan enkripsi/dekripsi XOR tanpa base64."""
    if not key:
        raise ValueError("Key tidak boleh kosong.")
    return ''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))

def xor_encrypt_base64(data: str, key: str) -> str:
    """Enkripsi XOR dan encode hasilnya ke base64 (jika butuh untuk dikirim)."""
    encrypted = xor_encrypt_decrypt(data, key)
    return base64.b64encode(encrypted.encode()).decode()

def xor_decrypt_base64(encoded_data: str, key: str) -> str:
    """Decode dari base64 dan lakukan XOR decrypt."""
    encrypted = base64.b64decode(encoded_data).decode()
    return xor_encrypt_decrypt(encrypted, key)

def embed_message_lsb(image_path: str, message: str) -> str:
    """Menyisipkan pesan ke gambar menggunakan LSB."""
    img = Image.open(image_path).convert("RGB")
    width, height = img.size

    full_message_data = message + "<END>"
    binary_data = text_to_binary(full_message_data)
    data_index = 0

    capacity_bits = width * height * 3
    if len(binary_data) > capacity_bits:
        raise ValueError(f"Message is too long ({len(binary_data)} bits) for image capacity ({capacity_bits} bits).")

    pixels = list(img.getdata())
    modified_pixels = []

    for pixel in pixels:
        r, g, b = pixel
        r_bin = list(format(r, '08b'))
        g_bin = list(format(g, '08b'))
        b_bin = list(format(b, '08b'))

        if data_index < len(binary_data):
            r_bin[-1] = binary_data[data_index]
            data_index += 1
        if data_index < len(binary_data):
            g_bin[-1] = binary_data[data_index]
            data_index += 1
        if data_index < len(binary_data):
            b_bin[-1] = binary_data[data_index]
            data_index += 1

        modified_pixels.append((
            int(''.join(r_bin), 2),
            int(''.join(g_bin), 2),
            int(''.join(b_bin), 2)
        ))

    modified_pixels += pixels[len(modified_pixels):]

    modified_img = Image.new(img.mode, img.size)
    modified_img.putdata(modified_pixels)

    base_name, ext = os.path.splitext(image_path)
    stego_image_path = f"{base_name}_stego{ext}"
    modified_img.save(stego_image_path)

    return stego_image_path

def extract_message_lsb(stego_image_path: str) -> str:
    """Mengambil pesan dari gambar dengan LSB decoding."""
    img = Image.open(stego_image_path).convert("RGB")
    pixels = list(img.getdata())
    binary_message = ""

    for pixel in pixels:
        r_bin = format(pixel[0], '08b')
        g_bin = format(pixel[1], '08b')
        b_bin = format(pixel[2], '08b')
        binary_message += r_bin[-1]
        binary_message += g_bin[-1]
        binary_message += b_bin[-1]

    message_chars = []
    for i in range(0, len(binary_message), 8):
        byte = binary_message[i:i+8]
        if len(byte) < 8:
            continue
        char = chr(int(byte, 2))
        message_chars.append(char)
        if ''.join(message_chars).endswith("<END>"):
            break

    return ''.join(message_chars).replace("<END>", "")