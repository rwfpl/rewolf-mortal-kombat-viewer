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

from dataclasses import dataclass
from typing import ClassVar, List, Tuple, Optional
import struct

STRUCT_USHORT_unpack = struct.Struct('<H').unpack
STRUCT_UINT_unpack = struct.Struct('<I').unpack


@dataclass
class GraDescriptor:
    file_size: int
    file_ids: List[int]


@dataclass
class ClippingBox:
    x_adjust: int
    y_adjust: int
    width: int
    height: int


@dataclass
class Color:
    r: int
    g: int
    b: int

    def tuple(self) -> Tuple[int, int, int]:
        return self.r, self.g, self.b


@dataclass
class ImageSize:
    width: int
    height: int


@dataclass
class Palette:
    colors: List[int]
    offset: int = 0
    on_disk_size: int = 0

    @staticmethod
    def FromBytes(buffer: memoryview, position: int) -> Optional['Palette']:
        ''' Palette as defined in original MK executable:
        struct Palette {
            __int16 length;
            __int16 colors[];
        };
        '''
        if position + 2 > len(buffer):
            return None
        colors_count = STRUCT_USHORT_unpack(buffer[position:position + 2])[0]
        if colors_count < 2 or colors_count > 256:
            return None
        colors_pos = position + 2
        if colors_pos + 2 * colors_count > len(buffer):
            return None
        unpacked_colors = struct.unpack_from('<%dH' % colors_count, buffer,
                                             colors_pos)
        if max(unpacked_colors) >= 0x8000:
            return None
        if len(set(unpacked_colors)) < 2 * len(unpacked_colors) / 3:
            return None
        # insert black color as a first entry for all palettes
        return Palette([0, ] + list(unpacked_colors),
                       position,
                       2 + 2*colors_count) # yapf: disable


@dataclass
class FileEntry:
    '''This struct mimics the one stored in MK executables:
    struct FileEntry {
        char *filename;
        int filesize;
        char flags;
        char dummy[3];
        int unk2_0;
        char *buffer;
        int unk2_2;
    };
    '''
    file_name_offset: int = -1
    file_size: int = -1
    flags: int = -1
    unk0: int = -1
    buffer: int = -1
    unk1: int = -1

    SIZE: ClassVar[int] = 6 * 4
    SIZE_PARTIAL: ClassVar[int] = 4 * 4
    STRUCT_UINT_4_unpack = struct.Struct('<4I').unpack
    STRUCT_UINT_6_unpack = struct.Struct('<6I').unpack

    def isValidPartial(self) -> bool:
        return (self.flags == 0x12 and self.unk0 == 0 and self.buffer == 0
                and self.unk1 == 0)

    def isValid(self) -> bool:
        return (self.file_name_offset != 0 and self.file_size != 0
                and self.isValidPartial())

    @staticmethod
    def FromBytes(buffer: memoryview) -> 'FileEntry':
        if len(buffer) < FileEntry.SIZE:
            return FileEntry()
        d = FileEntry.STRUCT_UINT_6_unpack(buffer[:FileEntry.SIZE])
        return FileEntry(*d)

    @staticmethod
    def FromBytesPartial(buffer: memoryview) -> 'FileEntry':
        if len(buffer) < FileEntry.SIZE_PARTIAL:
            return FileEntry()
        d = FileEntry.STRUCT_UINT_4_unpack(buffer[:FileEntry.SIZE_PARTIAL])
        return FileEntry(0, 0, *d)


@dataclass
class SpriteDescriptor:
    '''Sprite decriptors found in original MK executable:
    struct SpriteEntry
    {
        __int16 width;
        __int16 height;
        __int16 x;
        __int16 y;
        __int32 file_id_offset;
    };
    struct SpriteEntryNoXY
    {
        __int16 width;
        __int16 height;
        __int32 file_id_offset;
    };
    '''
    file_id: int
    offset: int
    width: int
    height: int
    x: int
    y: int
    data: List[int]
    number_of_colors: int = 0

    MIN_SIZE: ClassVar[int] = 8
    SIZE: ClassVar[int] = 12
    MAX_WIDTH: ClassVar[int] = 320
    MAX_HEIGHT: ClassVar[int] = 240
    STRUCT_SHORT_2_unpack = struct.Struct('<2h').unpack

    @staticmethod
    def __getIdOffset(id_offset: int) -> Tuple[int, int]:
        return id_offset >> 24, id_offset & 0xFFFFFF

    @staticmethod
    def FromBytes(buffer: memoryview) -> List['SpriteDescriptor']:
        if len(buffer) < SpriteDescriptor.MIN_SIZE:
            return []
        w = STRUCT_USHORT_unpack(buffer[:2])[0]
        if w >= SpriteDescriptor.MAX_WIDTH or w == 0:
            return []
        h = STRUCT_USHORT_unpack(buffer[2:4])[0]
        if h >= SpriteDescriptor.MAX_HEIGHT or h == 0:
            return []
        x, y = SpriteDescriptor.STRUCT_SHORT_2_unpack(buffer[4:8])
        ret = []
        if x >= -256 and x <= 256 and y >= -256 and y <= 256 and len(
                buffer) >= SpriteDescriptor.SIZE:
            id, offset = SpriteDescriptor.__getIdOffset(
                STRUCT_UINT_unpack(buffer[8:12])[0])
            ret.append(SpriteDescriptor(id, offset, w, h, x, y, []))
        id, offset = SpriteDescriptor.__getIdOffset(
            STRUCT_UINT_unpack(buffer[4:8])[0])
        ret.append(SpriteDescriptor(id, offset, w, h, 0, 0, []))
        return ret
