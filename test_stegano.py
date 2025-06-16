import os
import base64
from PIL import Image

def text_to_binary(text: str) -> str:
    return ''.join(format(ord(char), '08b') for char in text)

def binary_to_text(binary: str) -> str:
    chars = []
    for i in range(0, len(binary), 8):
        byte = binary[i:i + 8]
        if len(byte) == 8:
            chars.append(chr(int(byte, 2)))
    return ''.join(chars)

def xor_encrypt_base64(message: str, key: str) -> str:
    encrypted = ''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(message))
    return base64.b64encode(encrypted.encode()).decode()

def xor_decrypt_base64(encoded_message: str, key: str) -> str:
    decoded = base64.b64decode(encoded_message.encode())
    return ''.join(chr(b ^ ord(key[i % len(key)])) for i, b in enumerate(decoded))

def embed_message_lsb(image_path: str, message: str) -> str:
    img = Image.open(image_path).convert("RGB")
    pixels = list(img.getdata())

    full_message = message + "<END>"
    binary_data = text_to_binary(full_message)
    capacity = len(pixels) * 3
    if len(binary_data) > capacity:
        raise ValueError("Pesan terlalu panjang untuk gambar ini.")

    data_index = 0
    new_pixels = []

    for pixel in pixels:
        r, g, b = pixel
        r_bin = format(r, '08b')
        g_bin = format(g, '08b')
        b_bin = format(b, '08b')

        if data_index < len(binary_data):
            r_bin = r_bin[:-1] + binary_data[data_index]
            data_index += 1
        if data_index < len(binary_data):
            g_bin = g_bin[:-1] + binary_data[data_index]
            data_index += 1
        if data_index < len(binary_data):
            b_bin = b_bin[:-1] + binary_data[data_index]
            data_index += 1

        new_pixel = (int(r_bin, 2), int(g_bin, 2), int(b_bin, 2))
        new_pixels.append(new_pixel)

    if len(new_pixels) < len(pixels):
        new_pixels.extend(pixels[len(new_pixels):])

    new_img = Image.new("RGB", img.size)
    new_img.putdata(new_pixels)

    output_path = f"{os.path.splitext(image_path)[0]}_stego{os.path.splitext(image_path)[1]}"
    new_img.save(output_path)
    return output_path

def extract_message_lsb(image_path: str) -> str:
    img = Image.open(image_path).convert("RGB")
    pixels = list(img.getdata())

    binary_data = ""
    for pixel in pixels:
        for color in pixel:  # R, G, B
            binary_data += format(color, '08b')[-1]

    extracted = binary_to_text(binary_data)
    if "<END>" in extracted:
        return extracted.split("<END>")[0]
    else:
        return "[No END marker found]"

# MAIN TESTING CODE
if __name__ == "__main__":
    image_path = "karya_sepeda.png"
    secret_message = "Made By: Love"
    key = "12345"

    if not os.path.exists(image_path):
        print("[ERROR] Gambar tidak ditemukan.")
        exit()

    encrypted = xor_encrypt_base64(secret_message, key)
    print("[+] Encrypted (base64):", encrypted)

    try:
        stego_img_path = embed_message_lsb(image_path, encrypted)
        print("[+] Embedded to:", stego_img_path)
    except Exception as e:
        print("[ERROR] Gagal embed:", e)
        exit()

    try:
        extracted_encrypted = extract_message_lsb(stego_img_path)
        print("[+] Extracted:", extracted_encrypted)

        decrypted = xor_decrypt_base64(extracted_encrypted, key)
        print("[+] Decrypted message:", decrypted)

        if decrypted == secret_message:
            print("[✅] Berhasil! Pesan cocok.")
        else:
            print("[❌] Pesan tidak cocok.")
    except Exception as e:
        print("[ERROR] Gagal extract:", e)
