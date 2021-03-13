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

import time
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinter

from PIL import Image, ImageTk
from threading import Thread
from typing import List

import graph_util
import mkexec
import grafile
import mktypes


class Application(tk.Frame):
    def __init__(self, master=None) -> None:
        tk.Frame.__init__(self, master)

        self.photos: List[ImageTk.PhotoImage] = []
        self.animation_thread_running = False
        self.close_when_thread_is_finished = False
        self.grid(sticky=tk.N + tk.S + tk.E + tk.W, padx=4, pady=4)
        self.createWidgets()
        self.master.protocol('WM_DELETE_WINDOW', lambda: self.onClose())

    def onClose(self) -> None:
        if self.animation_thread_running:
            self.close_when_thread_is_finished = True
            self.animation_enabled.set(0)
        else:
            self.master.destroy()

    def parseMkExecutable(self, filename: str) -> None:
        self.mkexec = mkexec.MkExec(filename)

    def parseGraFile(self, gra_filename: str) -> None:
        gra_file = grafile.GraFile(self.mkexec, gra_filename)
        self.sprites = []
        self.checkbox_render_all.deselect()
        self.listbox_gra_entries.configure(state=tk.NORMAL)
        self.listbox_gra_entries.delete(0, tk.END)
        for s in gra_file.sprites.values():
            self.sprites.append(s)
            self.listbox_gra_entries.insert(
                tk.END, '%06x (%d, %d) (%d, %d)' %
                (s.offset, s.width, s.height, s.x, s.y))

    def loadMkExecutable(self, event):
        filename = filedialog.askopenfilename(filetypes=(('EXE files.',
                                                          '*.EXE'), ))
        if filename:
            self.string_mk_exe.set(filename)
            self.parseMkExecutable(self.string_mk_exe.get())

    def loadGraFile(self, event):
        filename = filedialog.askopenfilename(
            filetypes=(('GRA files.', '*.GRA'), ),
            initialdir=os.path.join(os.path.dirname(self.string_mk_exe.get()),
                                    'GRAPHICS'))
        if filename:
            self.string_gra_file.set(filename)
            self.parseGraFile(self.string_gra_file.get())

    def getScaledSpriteSize(
            self, sprite: mktypes.SpriteDescriptor) -> mktypes.ImageSize:
        scale = self.scale_slider.get()
        return mktypes.ImageSize(round(sprite.width * scale),
                                 round(sprite.height * scale))

    def drawBytesOnCanvas(self, img_buffer: List[int], width: int, height: int,
                          x: int, y: int,
                          palette: mktypes.Palette) -> mktypes.ImageSize:
        colored_sprite = graph_util.ApplyPalette(
            img_buffer, graph_util.PreparePalette(palette.colors))
        scale = self.scale_slider.get()
        img = Image.frombuffer('RGB', (width, height), colored_sprite, 'raw',
                               'RGB', 0, 1).resize((round(width * scale),
                                                    round(height * scale)))
        if x == 0 and y == 0:
            self.photos = []
        self.photos.append(ImageTk.PhotoImage(img))
        self.canvas.create_image(x, y, image=self.photos[-1], anchor=tk.NW)
        return mktypes.ImageSize(*img.size)

    def drawSpriteOnCanvas(self, sprite: mktypes.SpriteDescriptor, x: int,
                           y: int,
                           palette: mktypes.Palette) -> mktypes.ImageSize:
        return self.drawBytesOnCanvas(sprite.data, sprite.width, sprite.height,
                                      x, y, palette)

    def updatePaletteFrame(self) -> None:
        palette = self.getSelectedPalette()
        colors = graph_util.PreparePalette(palette.colors)
        max_color = len(palette.colors)
        for i in range(0, 256):
            if i < max_color:
                self.palette_boxes[i].configure(
                    bg='#' + format(colors[i].r, '02x') +
                    format(colors[i].g, '02x') + format(colors[i].b, '02x'))
            else:
                self.palette_boxes[i].configure(bg='white')

    def updatePalettesListBox(self, current_colors: List[int]) -> None:
        self.listbox_palette.delete(0, tk.END)
        selected_index = -1
        for p in self.palettes:
            self.listbox_palette.insert(
                tk.END, 'Pal_{:X} colors: {}'.format(p.offset, len(p.colors)))
            if current_colors == p.colors:
                selected_index = self.listbox_palette.size() - 1
        if selected_index != -1:
            self.listbox_palette.selection_set(selected_index)
        else:
            self.listbox_palette.selection_set(0)
        self.updatePaletteFrame()

    def renderSpriteList(self,
                         sprites: List[mktypes.SpriteDescriptor]) -> None:
        if not sprites:
            return
        self.updatePaletteFrame()
        self.canvas.update()
        canvas_width = self.canvas.winfo_width()
        max_height = 0
        current_x = 0
        current_y = 0
        for sprite in sprites:
            scaled_size = self.getScaledSpriteSize(sprite)
            if current_x + scaled_size.width > canvas_width:
                current_x = 0
                current_y += max_height
            actual_size = self.drawSpriteOnCanvas(sprite, current_x, current_y,
                                                  self.getSelectedPalette())
            current_x += actual_size.width
            if actual_size.height > max_height:
                max_height = actual_size.height

    def renderAllSprites(self) -> None:
        self.renderSpriteList(self.sprites)

    def getSelectedSprites(self) -> List[mktypes.SpriteDescriptor]:
        if self.render_all.get():
            return self.sprites
        else:
            selected_sprites = self.listbox_gra_entries.curselection()
            return [self.sprites[i] for i in selected_sprites]

    def getSelectedPalette(self) -> mktypes.Palette:
        cs = self.listbox_palette.curselection()
        if cs:
            return self.palettes[cs[0]]
        return mktypes.Palette([])

    def getCurrentPaletteColors(self) -> List[int]:
        return self.getSelectedPalette().colors

    def saveAnimated(self, filename: str) -> None:
        sprites = self.getSelectedSprites()
        palette = self.getSelectedPalette()
        clipping_box = graph_util.CalculateClippingBox(sprites)
        images = []
        for s in sprites:
            buf = graph_util.AddClippingBox(s, clipping_box, -1)
            colored_sprite = graph_util.ApplyPalette(
                buf, graph_util.PreparePalette(palette.colors))
            images.append(
                Image.frombuffer('RGB',
                                 (clipping_box.width, clipping_box.height),
                                 colored_sprite, 'raw', 'RGB', 0, 1))
        try:
            images[0].save(filename,
                           save_all=True,
                           append_images=images[1:],
                           optimize=True,
                           duration=round(1000 / self.speed_var.get()),
                           loop=0)
        except ValueError as e:
            messagebox.showerror('Error', str(e))

    def animate(self) -> None:
        self.animation_thread_running = True
        sprites = self.getSelectedSprites()
        clipping_box = graph_util.CalculateClippingBox(sprites)

        sprite_index = 0
        while self.animation_enabled.get():
            if sprites:
                s = sprites[sprite_index]
                buf = graph_util.AddClippingBox(s, clipping_box, -1)
                self.drawBytesOnCanvas(buf, clipping_box.width,
                                       clipping_box.height, 0, 0,
                                       self.getSelectedPalette())
                sprite_index += 1
                sprite_index %= len(sprites)
            time.sleep(1.0 / self.speed_var.get())
        self.animation_thread_running = False

    def animateSprites(self) -> None:
        self.current_sprite_animation_index = 0
        self.animation_thread = Thread(target=lambda: self.animate())
        self.animation_thread.start()

    def onPaletteSelect(self, event) -> None:
        self.updatePaletteFrame()
        if not self.animation_enabled.get():
            self.renderSpriteList(self.getSelectedSprites())

    def updatePaletteListForSprites(
            self, sprites: List[mktypes.SpriteDescriptor]) -> None:
        if not sprites:
            return
        min_colors = 0
        for sprite in sprites:
            if sprite.number_of_colors >= min_colors:
                min_colors = sprite.number_of_colors
        current_colors = self.getCurrentPaletteColors()
        self.palettes = list(
            self.mkexec.GetSuitablePalettes(min_colors).values())
        self.updatePalettesListBox(current_colors)

    def onSpriteSelect(self, event) -> None:
        sprites = self.getSelectedSprites()
        self.updatePaletteListForSprites(sprites)
        self.renderSpriteList(sprites)

    def onScaleChange(self) -> None:
        if not self.animation_enabled.get():
            self.renderSpriteList(self.getSelectedSprites())

    def onRenderAllChange(self) -> None:
        if self.render_all.get():
            self.listbox_gra_entries.configure(state=tk.DISABLED)
            self.updatePaletteListForSprites(self.sprites)
            self.renderAllSprites()
        else:
            self.listbox_gra_entries.configure(state=tk.NORMAL)
            self.onSpriteSelect(None)

    def onMultiSelectChange(self) -> None:
        if self.multiple_selection_enabled.get():
            self.listbox_gra_entries.configure(selectmode=tk.MULTIPLE)
        else:
            self.listbox_gra_entries.configure(selectmode=tk.BROWSE)
            cur_sel = self.listbox_gra_entries.curselection()
            if cur_sel:
                self.listbox_gra_entries.selection_clear(
                    cur_sel[0], cur_sel[-1])
                self.listbox_gra_entries.selection_set(cur_sel[0])

    def onAnimationChange(self) -> None:
        if self.animation_enabled.get():
            self.animateSprites()
        else:
            self.renderSpriteList(self.getSelectedSprites())

    def saveStatic(self, filename: str) -> None:
        sprites = self.getSelectedSprites()
        palette = self.getSelectedPalette()
        img = graph_util.GetSpritesImage(sprites, palette)
        try:
            img.save(filename)
        except ValueError as e:
            messagebox.showerror('Error', str(e))

    def onSave(self) -> None:
        filename = filedialog.asksaveasfilename(
            filetypes=(('PNG files.', '*.png'), ('GIF files.', '*.gif')),
            initialdir=os.path.join(os.path.dirname(self.string_mk_exe.get()),
                                    'GRAPHICS'))
        if self.animation_enabled.get():
            self.saveAnimated(filename)
        else:
            self.saveStatic(filename)

    def createWidgets(self) -> None:
        top = self.winfo_toplevel()
        top.rowconfigure(0, weight=1)
        top.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=10)

        self.label_mk_exe = tk.Label(self, text='Mortal Kombat executable:')
        self.label_mk_exe.grid(column=0, row=0, sticky='NW')

        self.string_mk_exe = tk.StringVar()
        self.text_mk_exe = tk.Entry(self, textvariable=self.string_mk_exe)
        self.text_mk_exe.grid(column=0, row=1, sticky='NEW')
        self.text_mk_exe.bind("<Button-1>", lambda e: self.loadMkExecutable(e))

        self.label_gra_file = tk.Label(self, text='GRA file:')
        self.label_gra_file.grid(column=1, row=0, columnspan=2, sticky='NW')

        self.string_gra_file = tk.StringVar()
        self.text_gra_file = tk.Entry(self, textvariable=self.string_gra_file)
        self.text_gra_file.grid(column=1, row=1, columnspan=2, sticky='NEW')
        self.text_gra_file.bind("<Button-1>", lambda e: self.loadGraFile(e))

        self.pal_sprites_frame = tk.Frame(self)
        self.pal_sprites_frame.grid(column=0, row=2, rowspan=3, sticky='NESW')
        self.pal_sprites_frame.rowconfigure(1, weight=1)
        self.pal_sprites_frame.columnconfigure(0, weight=1)
        self.pal_sprites_frame.columnconfigure(2, weight=1)

        self.label_palettes = tk.Label(self.pal_sprites_frame,
                                       text='Palettes:')
        self.label_palettes.grid(column=0, row=0, sticky='NW')
        self.lb_pal_scroll = tk.Scrollbar(self.pal_sprites_frame,
                                          orient=tk.VERTICAL)
        self.listbox_palette = tk.Listbox(
            self.pal_sprites_frame,
            yscrollcommand=self.lb_pal_scroll.set,
            exportselection=0)
        self.lb_pal_scroll.config(command=self.listbox_palette.yview)
        self.listbox_palette.grid(column=0, row=1, sticky='NESW')
        self.lb_pal_scroll.grid(column=1, row=1, sticky='NS')
        self.listbox_palette.bind('<<ListboxSelect>>',
                                  lambda e: self.onPaletteSelect(e))

        self.label_sprites = tk.Label(self.pal_sprites_frame, text='Sprites:')
        self.label_sprites.grid(column=2, row=0, sticky='NW')
        self.lb_gra_scroll = tk.Scrollbar(self.pal_sprites_frame,
                                          orient=tk.VERTICAL)
        self.listbox_gra_entries = tk.Listbox(
            self.pal_sprites_frame,
            yscrollcommand=self.lb_gra_scroll.set,
            exportselection=0)
        self.lb_gra_scroll.config(command=self.listbox_gra_entries.yview)
        self.listbox_gra_entries.grid(column=2, row=1, sticky='NESW')
        self.lb_gra_scroll.grid(column=3, row=1, sticky='NS')
        self.listbox_gra_entries.bind('<<ListboxSelect>>',
                                      lambda e: self.onSpriteSelect(e))

        self.canvas = tk.Canvas(self, bg='#FFFFFF')
        self.canvas.grid(column=1, row=2, columnspan=3, sticky='NESW')
        self.canvas_image = Image.new("RGB", (0, 0), color=(255, 255, 255))

        self.pallette_frame = tk.Frame(self)
        self.pallette_frame.grid(column=1, row=3, columnspan=3, sticky='W')
        self.palette_boxes = []
        for i in range(0, 4):
            for j in range(0, 64):
                box = tk.Canvas(self.pallette_frame,
                                width=12,
                                height=12,
                                bg='white')
                box.grid(column=j, row=i, sticky='W')
                self.palette_boxes.append(box)

        self.control_frame = tk.Frame(self)
        self.control_frame.grid(column=1, row=4, columnspan=2, sticky='NESW')
        self.control_frame.columnconfigure(2, weight=1)
        self.scale_slider = tk.Scale(self.control_frame,
                                     label='Scale:',
                                     from_=1,
                                     to=10,
                                     orient=tk.HORIZONTAL,
                                     resolution=0.1,
                                     command=lambda e: self.onScaleChange())
        self.scale_slider.grid(column=1, row=0, sticky='WE')

        self.render_all = tk.IntVar()
        self.checkbox_render_all = tk.Checkbutton(
            self.control_frame,
            variable=self.render_all,
            text='Render all sprites in one view',
            command=lambda: self.onRenderAllChange())
        self.checkbox_render_all.grid(column=0, row=0, sticky='W')

        self.multiple_selection_enabled = tk.IntVar()
        self.checkbox_multi_select = tk.Checkbutton(
            self.control_frame,
            variable=self.multiple_selection_enabled,
            text='Multiple sprite selection mode',
            command=lambda: self.onMultiSelectChange())
        self.checkbox_multi_select.grid(column=0, row=1, sticky='W')

        self.animation_enabled = tk.IntVar()
        self.checkbox_animation = tk.Checkbutton(
            self.control_frame,
            variable=self.animation_enabled,
            text='Enable animation',
            command=lambda: self.onAnimationChange())
        self.checkbox_animation.grid(column=0, row=2, sticky='W')
        self.speed_var = tk.DoubleVar(value=12.0)
        self.speed_slider = tk.Scale(self.control_frame,
                                     label='Animation speed:',
                                     from_=1,
                                     to=50,
                                     orient=tk.HORIZONTAL,
                                     variable=self.speed_var)
        self.speed_slider.grid(column=1, row=2, sticky='W')

        self.button_save = tk.Button(self.control_frame,
                                     text='Save',
                                     padx=25,
                                     command=lambda: self.onSave())
        self.button_save.grid(column=2, row=0, rowspan=3, sticky='NES')


app = Application()
app.master.title('Mortal Kombat GRA viewer')
app.mainloop()
