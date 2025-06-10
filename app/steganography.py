import os
from PIL import Image

def text_to_binary(text: str) -> str:
    """Converts a string to its binary representation."""
    binary = ''.join(format(ord(char), '08b') for char in text)
    return binary

def binary_to_text(binary: str) -> str:
    """Converts a binary string back to text."""
    if len(binary) % 8 != 0:
        binary = '0' * (8 - (len(binary) % 8)) + binary

    if not binary: # Handle empty binary string case
        return ""

    try:
        n = int(binary, 2)
        num_bytes = (n.bit_length() + 7) // 8
        if num_bytes == 0 and n == 0:
            num_bytes = 1

        return n.to_bytes(num_bytes, 'big').decode('utf-8')
    except ValueError: 
        return "[Invalid binary data]"
    except UnicodeDecodeError:
        
        return "[Error decoding message]"

def xor_encrypt_decrypt(message: str, key: str) -> str:
    """
    Performs XOR encryption (or decryption) on a message using a key.
    Since XOR is symmetric, the same function can be used for both.
    """
    if not key:
        raise ValueError("Encryption key cannot be empty.")
    
    xor_result = []
    for i in range(len(message)):
        char_message = ord(message[i])
        char_key = ord(key[i % len(key)])  
        xor_result.append(chr(char_message ^ char_key))
    return "".join(xor_result)


def embed_message_lsb(image_path: str, message: str) -> str:
    """
    Embeds a message into an image's least significant bits (LSB).
    Returns the path to the steganographic image.
    """
    img = Image.open(image_path).convert("RGB")
    width, height = img.size
    
    full_message_data = message + "<END>" 
    binary_data = text_to_binary(full_message_data)
    data_index = 0

    capacity_bits = width * height * 3 
    if len(binary_data) > capacity_bits:
        raise ValueError(f"Message is too long ({len(binary_data)} bits) to embed in this image ({capacity_bits} bits).")

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
        
        modified_pixels.append((int("".join(r_bin), 2), int("".join(g_bin), 2), int("".join(b_bin), 2)))


    modified_img = Image.new(img.mode, img.size)
    modified_img.putdata(modified_pixels)

    base_name, ext = os.path.splitext(image_path)
    stego_image_path = f"{base_name}_stego{ext}"
    modified_img.save(stego_image_path)
    
    return stego_image_path


def extract_message_lsb(stego_image_path: str) -> str:
    """
    Extracts a message from an image's least significant bits (LSB).
    Returns the extracted message.
    """
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

    decoded_message = ""
    i = 0
    # Process the binary string in 8-bit (byte) chunks
    while i + 8 <= len(binary_message):
        byte = binary_message[i : i+8]
        char = binary_to_text(byte)
        
        current_decoded_segment = binary_to_text(binary_message[:i+8])
        if "<END>" in current_decoded_segment:
            return current_decoded_segment[:current_decoded_segment.index("<END>")]
        
        decoded_message += char
        i += 8
    
    return decoded_message