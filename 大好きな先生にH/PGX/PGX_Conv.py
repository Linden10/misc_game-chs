import os
import struct
from PIL import Image
import io
import hexdump

def custom_lzss_decompress(input_bytes, output_size):
    # ... (Your custom_lzss_decompress function remains the same)
    # Add debugging print statements here to track key variables (dst, ctl, offset, count, input_pos)
    dict_size = 0x1000
    dict_pos = 0xFEE
    dict = bytearray(dict_size)

    output_buffer = bytearray(output_size)
    output_ptr = 0
    output_end = output_size

    control = 0
    input_pos = 0
    try:
        while output_ptr < output_end:
            control >>= 1
            if not (control & 0x100):
                #print(f"Reading control byte at input_pos: {input_pos}")
                control = input_bytes[input_pos] | 0xFF00
                input_pos += 1
            if control & 1:
                #print(f"Reading literal byte at input_pos: {input_pos}")
                byte = input_bytes[input_pos]
                dict[dict_pos] = output_buffer[output_ptr] = byte
                output_ptr += 1
                dict_pos = (dict_pos + 1) % dict_size
                input_pos += 1
                continue
            tmp1 = input_bytes[input_pos]
            tmp2 = input_bytes[input_pos + 1]
            input_pos += 2
            look_behind_pos = (((tmp2 & 0xF0) << 4) | tmp1) % dict_size
            repetitions = (~tmp2 & 0xF) + 3
            #print(f"Reading offset/length at input_pos: {input_pos - 2}, offset: {look_behind_pos}, repetitions: {repetitions}")
            while repetitions > 0 and output_ptr < output_end:
                dict[dict_pos] = output_buffer[output_ptr] = dict[look_behind_pos]
                output_ptr += 1
                dict_pos = (dict_pos + 1) % dict_size
                look_behind_pos = (look_behind_pos + 1) % dict_size
                repetitions -= 1
    except IndexError:
        raise EOFError("Unexpected end of input")
    return output_buffer

def custom_lzss_compress(input_bytes, output_size):
    dict_size = 0x1000
    dict_pos = 0xFEE
    dict = bytearray(dict_size)
    
    output_buffer = bytearray()
    
    control = 0
    control_bits_count = 0
    input_pos = 0
    input_end = len(input_bytes)
    
    while input_pos < input_end:
        match_found = False
        best_match_offset = -1
        best_match_length = 0
        
        for offset in range(1, 0x1000):
            match_length = 0
            for i in range(min(0xF, input_end - input_pos)):
                if input_pos + i < input_end and input_bytes[input_pos + i] == dict[(dict_pos - offset + i) % dict_size]:
                    match_length += 1
                else:
                    break
            if match_length > best_match_length:
                best_match_length = match_length
                best_match_offset = offset
        
        if best_match_length >= 3 :
            match_found = True
            
            if best_match_length < 3:
                best_match_length = 3
                
            control |= (0 << control_bits_count)
            control_bits_count += 1
            if control_bits_count == 8:
                output_buffer.append(control)
                control = 0
                control_bits_count = 0
            output_buffer.extend(struct.pack('<B',((best_match_offset >> 4) & 0xFF) | ((best_match_length - 3) << 4)))
            for i in range(best_match_length):
                dict[dict_pos] = input_bytes[input_pos]
                dict_pos = (dict_pos + 1) % dict_size
                input_pos += 1
        else:
            match_found = False
            control |= (1 << control_bits_count)
            control_bits_count += 1
            if control_bits_count == 8:
                output_buffer.append(control)
                control = 0
                control_bits_count = 0
            output_buffer.extend(input_bytes[input_pos:input_pos+1])
            dict[dict_pos] = input_bytes[input_pos]
            dict_pos = (dict_pos + 1) % dict_size
            input_pos += 1

    if control_bits_count > 0:
        output_buffer.append(control)

    return output_buffer


class PGXImage:
    def __init__(self, path):
        self.path = path
        self.width = 0
        self.height = 0
        self.bpp = 0
        self.packed_size = 0
        self.flags = 0
        self.pixel_data = None
        self.gms_info = None
        self.read_header()

    def read_header(self):
        try:
            with open(self.path, 'rb') as f:
                f.seek(8)  # Skip magic number (4 bytes) + 4 bytes
                header_data = f.read(20)
                self.width, self.height = struct.unpack('<II', header_data[:8])
                self.bpp = 32 if (struct.unpack('<H', header_data[8:10])[0] & 1) else 24
                self.packed_size = struct.unpack('<I', header_data[12:16])[0]
                self.flags = struct.unpack('<H', header_data[16:18])[0]

                # Check for enough data
                file_size = os.path.getsize(self.path)
                if file_size < 24 + self.packed_size:
                    raise IOError(f"File too short. Expected at least {24 + self.packed_size} bytes, got {file_size}")

                print(f"Header: {header_data.hex()}")
                print(f"Width: {self.width}, Height: {self.height}, BPP: {self.bpp}, Packed Size: {self.packed_size}, Flags: {self.flags}")
        except Exception as e:
            print(f"Error reading header: {e}")
            raise


    def read_pixel_data(self):
        try:
            with open(self.path, 'rb') as f:
                #The header is already read in read_header(), no need to re-read it here
                f.seek(8)  # Skip magic number (4 bytes) + 4 bytes
                self.width = struct.unpack('<I', f.read(4))[0]
                self.height = struct.unpack('<I', f.read(4))[0]
                transparent = struct.unpack('<H', f.read(2))[0] != 0
                f.read(2)  # Skip 2 bytes
                self.packed_size = struct.unpack('<I', f.read(4))[0]

                f.seek(0, io.SEEK_END)  # Go to end of file
                f.seek(f.tell() - self.packed_size)  # Go to beginning of packed data
                compressed_data = f.read(self.packed_size)

                if len(compressed_data) != self.packed_size:
                    raise IOError(
                        f"Incorrect compressed image data size read. Expected {self.packed_size}, got {len(compressed_data)}")

                # Decompress data
                self.pixel_data = custom_lzss_decompress(compressed_data, self.width * self.height * 4)


                # Verify decompressed data size
                print(f"Dimensions: {self.width}x{self.height}, BPP: {self.bpp}, Packed Size: {self.packed_size}")
                print(f"Decompressed data length: {len(self.pixel_data)}")
                print(f"Expected data length: {self.width * self.height * 4}")
                if len(self.pixel_data) != self.width * self.height * 4:
                    raise ValueError(
                        f"Decompressed data size mismatch. Expected {self.width * self.height * 4}, got {len(self.pixel_data)}")

        except EOFError as e:
            print(f"Decompression Error: {e}")
            raise
        except IOError as e:
            print(f"IO Error: {e}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred during processing: {e}")
            raise


    def read_gms(self, f):
        try:
            header = bytearray(f.read(16))
            swap_indices = [(13, 9), (15, 11), (4, 8), (6, 10)]
            for i, j in swap_indices:
                header[i], header[j] = header[j], header[i]
            unpacked_size = struct.unpack('<I', header[12:16])[0]
            self.gms_info = bytearray(unpacked_size)
            compressed_gms_data = self.read_exact_bytes(f, unpacked_size)

            if len(compressed_gms_data) != unpacked_size:
                raise IOError(f"Incorrect compressed GMS data size read. Expected {unpacked_size}, got {len(compressed_gms_data)}")

            self.gms_info = custom_lzss_decompress(compressed_gms_data, unpacked_size)
            for i in range(len(self.gms_info)):
                self.gms_info[i] ^= 0xFF  # XOR with 0xFF

            # Print gms_info in various formats for analysis
            print("GMS info (hex):", self.gms_info.hex())
            print("GMS info (bytes):", self.gms_info)
            try:
                print("GMS info (utf-8):", self.gms_info.decode('utf-8'))  # Attempt UTF-8 decoding
            except UnicodeDecodeError:
                print("GMS info (utf-8 decoding failed)")
            try:
                print("GMS info (shift-jis):", self.gms_info.decode('shift-jis'))  # Attempt Shift-JIS decoding
            except UnicodeDecodeError:
                print("GMS info (shift-jis decoding failed)")
            return unpacked_size

        except EOFError as e:
            print(f"GMS Decompression Error: {e}")
            raise
        except IOError as e:
            print(f"GMS IO Error: {e}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred during GMS processing: {e}")
            raise

    def read_exact_bytes(self, f, num_bytes):
        data = bytearray()
        bytes_read = 0
        while bytes_read < num_bytes:
            byte = f.read(1)
            if not byte:
                raise EOFError(f"Unexpected end of file while reading data at byte {bytes_read}. Needed {num_bytes} bytes.")
            data.extend(byte)
            bytes_read += 1
        return data

    def save_image(self, output_path):
        try:
            if self.bpp == 32:
                # Handle BGRA to RGBA conversion
                rgba_data = bytearray()
                for i in range(0, len(self.pixel_data), 4):
                    rgba_data.extend([self.pixel_data[i+2], self.pixel_data[i+1], self.pixel_data[i], self.pixel_data[i+3]])
                img = Image.frombytes('RGBA', (self.width, self.height), bytes(rgba_data))
            else:
                # Handle RGB to BGR conversion
                bgr_data = bytearray()
                for i in range(0, len(self.pixel_data), 3):
                    bgr_data.extend([self.pixel_data[i+2], self.pixel_data[i+1], self.pixel_data[i]])
                img = Image.frombytes('RGB', (self.width, self.height), bytes(bgr_data))
            img.save(output_path, 'PNG', compression=None)
            print(f"Image saved successfully to {output_path}")
        except Exception as e:
            print(f"Error saving image {output_path}: {e}")

    def write_pgx_file(self, template_path, output_path, image_data):
        try:
            with open(template_path, 'rb') as template_file, open(output_path, 'wb') as output_file:
                # Copy header from template file (except for packed_size)
                header = template_file.read(20) #Read only the first 20 bytes of the header, excluding packed_size
                output_file.write(header)

                # Copy GMS data from template file (if present)
                if self.flags & 0x1000:
                    gms_data_size = struct.unpack('<I', header[12:16])[0]
                    gms_data = template_file.read(gms_data_size)
                    output_file.write(gms_data)

                # Write compressed image data
                compressed_image_data = custom_lzss_compress(image_data, len(image_data))
                output_file.write(compressed_image_data)

                # Update packed_size in the header
                with open(output_path, 'r+b') as f:
                    f.seek(16)  # Seek to the packed_size field in the header
                    f.write(struct.pack('<I', len(compressed_image_data)))  # Write the actual packed size

                print(f"PGX file written successfully to {output_path}")
        except Exception as e:
            print(f"Error writing PGX file: {e}")

def extract_pgx_files(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file_name in os.listdir(input_folder):
        if file_name.lower().endswith('.pgx'):
            input_path = os.path.join(input_folder, file_name)
            output_path = os.path.join(output_folder, os.path.splitext(file_name)[0] + '.png')
            print(f'Processing {input_path}:')
            try:
                pgx_image = PGXImage(input_path)
                pgx_image.read_pixel_data()
                pgx_image.save_image(output_path)
                print(f'Saved {output_path}')
            except Exception as e:
                print(f"Error processing {input_path}: {e}")

def convert_files(input_folder, output_folder, template_path):
    template_pgx = PGXImage(template_path) #Read the template PGX file once

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file_name in os.listdir(input_folder):
        if file_name.lower().endswith('.png'):
            input_path = os.path.join(input_folder, file_name)
            output_path = os.path.join(output_folder, os.path.splitext(file_name)[0] + '.pgx')
            print(f'Processing {input_path}:')
            try:
                img = Image.open(input_path)
                pixel_data = bytearray(img.tobytes())
                if img.mode == 'RGBA':
                    bgra_data = bytearray()
                    for i in range(0, len(pixel_data), 4):
                        bgra_data.extend([pixel_data[i+2], pixel_data[i+1], pixel_data[i], pixel_data[i+3]])
                    pixel_data = bgra_data
                elif img.mode == 'RGB':
                    bgr_data = bytearray()
                    for i in range(0, len(pixel_data), 3):
                        bgr_data.extend([pixel_data[i+2], pixel_data[i+1], pixel_data[i]])
                    pixel_data = bgr_data

                # Use the template PGX image's header and flags
                template_pgx.write_pgx_file(template_path, output_path, pixel_data) 
                print(f'Saved {output_path}')
            except Exception as e:
                print(f"Error processing {input_path}: {e}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 4 or sys.argv[1] not in ('extract', 'convert'):
        print(f'Usage: {sys.argv[0]} extract <input_folder> <output_folder>')
        print(f'Usage: {sys.argv[0]} convert <input_folder> <output_folder> <template_path>')
        sys.exit(1)

    command = sys.argv[1]
    input_folder = sys.argv[2]
    output_folder = sys.argv[3]

    if command == 'extract':
        extract_pgx_files(input_folder, output_folder)
    elif command == 'convert':
        if len(sys.argv) != 5:
            print(f'Usage: {sys.argv[0]} convert <input_folder> <output_folder> <template_path>')
            sys.exit(1)
        template_path = sys.argv[4]
        convert_files(input_folder, output_folder, template_path)
