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

import os
from typing import List, Dict
import mktypes
from collections import defaultdict


class MkExec:
    # sprite_files: Dict[int, mktypes.SpriteFile]
    sprite_files: Dict[int, List[mktypes.SpriteDescriptor]]
    palettes: Dict[int, mktypes.Palette]

    def __init__(self, mkexe_file_name: str) -> None:
        self.palettes = dict()
        self.sprite_files = defaultdict(list)
        try:
            with open(mkexe_file_name, 'rb') as f:
                self.exec_data = memoryview(f.read())
        except:
            return
        self.__paletteBruteForce()
        self.__spriteBruteForce()

    def __paletteBruteForce(self) -> None:
        if not self.exec_data:
            return
        # generic palette search
        pos = 0
        while pos < len(self.exec_data):
            palette = mktypes.Palette.FromBytes(self.exec_data, pos)
            if not palette:
                pos += 1
                continue
            self.palettes[pos] = palette
            pos += palette.on_disk_size

    def __spriteBruteForce(self) -> None:
        # Generic sprite descriptor search.
        pos = 0
        while pos < len(self.exec_data):
            potential_sprites = mktypes.SpriteDescriptor.FromBytes(
                self.exec_data[pos:pos + mktypes.SpriteDescriptor.SIZE])
            for s in potential_sprites:
                self.sprite_files[s.file_id].append(s)
            pos += 1

    def FindFileId(self, file_name: str) -> mktypes.GraDescriptor:
        if not self.exec_data:
            return mktypes.GraDescriptor(0, [])
        try:
            file_size = os.path.getsize(file_name)
        except:
            return mktypes.GraDescriptor(0, [])

        ret = []
        pos = 0
        while pos < len(self.exec_data) - 4:
            # Look for the GRA file size in the MK executable.
            dword_0 = mktypes.STRUCT_UINT_unpack(self.exec_data[pos:pos +
                                                                4])[0]
            if dword_0 != file_size:
                pos += 1
                continue
            partial_file_entry = mktypes.FileEntry.FromBytesPartial(
                self.exec_data[pos + 4:pos + mktypes.FileEntry.SIZE])
            if not partial_file_entry.isValidPartial():
                pos += 1
                continue
            # GRA file size found, now look for the begining of the GRA files table.
            file_id = 0
            file_table_pos = pos - 4 - mktypes.FileEntry.SIZE
            while file_table_pos >= 0:
                file_entry = mktypes.FileEntry.FromBytes(
                    self.exec_data[file_table_pos:file_table_pos +
                                   mktypes.FileEntry.SIZE])
                if file_entry.isValid():
                    file_id += 1
                    file_table_pos -= mktypes.FileEntry.SIZE
                else:
                    ret.append(file_id)
                    break
            pos += 1
        return mktypes.GraDescriptor(file_size, ret)

    def GetSuitablePalettes(self,
                            min_colors: int) -> Dict[int, mktypes.Palette]:
        return {
            pos: palette
            for pos, palette in self.palettes.items()
            if len(self.palettes[pos].colors) >= min_colors
        }

    def GetSuitableSprites(self, file_id: int,
                           file_size: int) -> List[mktypes.SpriteDescriptor]:
        if file_id not in self.sprite_files:
            return []
        return [s for s in self.sprite_files[file_id] if s.offset < file_size]
