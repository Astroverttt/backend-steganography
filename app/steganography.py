import os
import base64
from PIL import Image


def text_to_binary(text: str) -> str:
    return ''.join(format(ord(char), '08b') for char in text)

def binary_to_text(binary: str) -> str:
    chars = []
    for i in range(0, len(binary), 8):
        byte = binary[i:i+8]
        if len(byte) == 8:
            chars.append(chr(int(byte, 2)))
    return ''.join(chars)

def xor_encrypt_decrypt(data: str, key: str) -> str:
    if not key:
        raise ValueError("Key tidak boleh kosong.")
    return ''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))

def xor_encrypt_base64(data: str, key: str) -> str:
    encrypted = xor_encrypt_decrypt(data, key)
    return base64.b64encode(encrypted.encode()).decode()

def xor_decrypt_base64(encoded_data: str, key: str) -> str:
    encrypted = base64.b64decode(encoded_data).decode()
    return xor_encrypt_decrypt(encrypted, key)

def embed_message_lsb(image_path: str, message: str) -> str:
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
    img = Image.open(stego_image_path).convert("RGB")
    pixels = list(img.getdata())

    bits = []
    for r, g, b in pixels:
        bits.append(format(r, '08b')[-1])
        bits.append(format(g, '08b')[-1])
        bits.append(format(b, '08b')[-1])

    chars = []
    for i in range(0, len(bits), 8):
        byte = ''.join(bits[i:i+8])
        if len(byte) < 8:
            continue
        char = chr(int(byte, 2))
        chars.append(char)
        if ''.join(chars[-5:]) == "<END>":  
            break

    return ''.join(chars).replace("<END>", "")