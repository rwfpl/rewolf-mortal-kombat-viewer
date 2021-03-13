'''
 Mortal Kombat uncompressed GRA files viewer
 
 Copyright (c) 2021 ReWolf
 http://blog.rewolf.pl/
 
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU Lesser General Public License as published
 by the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU Lesser General Public License for more details.
 
 You should have received a copy of the GNU Lesser General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from typing import Dict, List
import mktypes
import mkexec


def GetNumberOfColors(buf):
    return max(buf) - 1


def DecodePixels(data: memoryview,
                 width: int,
                 height: int,
                 alpha_color: int = -1,
                 palette_shift: int = 0) -> List[int]:
    output = []
    width_bak = width & 0xFF

    current_offset = 0
    while height != 0 and current_offset + 4 <= len(data):
        code = mktypes.STRUCT_UINT_unpack(data[current_offset:current_offset +
                                               4])[0]
        current_offset += 4
        bit0 = code & 1
        code >>= 1
        bit1 = code & 1
        if bit0:
            if code > width * height:
                return []
            output.extend([alpha_color] * code)
        elif bit1:
            code >>= 1
            pixel = code & 0xFF
            code >>= 8
            output.extend([(pixel + palette_shift) & 0xFF] * code)
        else:
            code >>= 1
            read_length = (code + 3) & 0xFFFFFFFC
            data_read = data[current_offset:current_offset + code]
            current_offset += read_length
            output.extend([(pixel + palette_shift) & 0xFF
                           for pixel in data_read])

        width -= code
        if width != 0:
            continue

        width = width_bak
        height -= 1

    return output if height == 0 else []


class GraFile:
    sprites: Dict[int, mktypes.SpriteDescriptor]

    def __init__(self, mkobj: mkexec.MkExec, file_name: str) -> None:
        self.mkobj = mkobj
        self.sprites = dict()
        try:
            with open(file_name, 'rb') as f:
                self.data = memoryview(f.read())
        except:
            return
        gra_descriptor = self.mkobj.FindFileId(file_name)
        for id in gra_descriptor.file_ids:
            sprites = self.mkobj.GetSuitableSprites(id,
                                                    gra_descriptor.file_size)
            if not sprites:
                continue
            temp_sprites = dict()
            for sprite in sprites:
                buffer = DecodePixels(self.data[sprite.offset:], sprite.width,
                                      sprite.height)
                if len(buffer):
                    sprite.data = buffer
                    sprite.number_of_colors = GetNumberOfColors(buffer)
                    temp_sprites[sprite.offset] = sprite
            if len(temp_sprites) > len(self.sprites):
                self.sprites = temp_sprites
