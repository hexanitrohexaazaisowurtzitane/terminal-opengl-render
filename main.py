import curses
import numpy as np
import os
import time
from OpenGL.GL import *
from OpenGL.GLU import *
import pygame
from pygame.locals import *

from edit import TextEditor, JsonModelRenderer


class TerminalRenderer:
    def __init__(self):
        self.stdscr = None
        self.term_height = self.term_width = 0
        self.split_ratio = 0.7
        
        pygame.init()
        self.model_renderer = JsonModelRenderer()
        
        self.last_time = time.time()
        self.frame_count = self.fps = 0

        self.rotation_angle = 0.0
        self.auto_rotate = True
        self.last_rotation_angle = 0.0
        
        # cam
        self.camera_distance = 5.0
        self.camera_rotation_x = self.camera_rotation_y = 0.0
        self.camera_position_x = self.camera_position_y = 0.0
        
        # mouse
        self.left_dragging = self.right_dragging = False
        self.last_mouse_x = self.last_mouse_y = 0
        self.mouse_sensitivity = 2.0
        self.error_message = ""
        
    def setup_screen(self):
        self.stdscr = curses.initscr()
        curses.start_color()
        curses.curs_set(1)
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        self.stdscr.nodelay(1)
        
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        print("\033[?1003h") # no idea dont care
        
        self.term_height, self.term_width = self.stdscr.getmaxyx()
        
        self.init_color_pairs()
        self.update_dimensions()
        
        pygame.display.set_mode((self.gl_width, self.gl_height), DOUBLEBUF | OPENGL | HIDDEN)
        
        glViewport(0, 0, self.gl_width, self.gl_height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, self.gl_width / self.gl_height, 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_DEPTH_TEST)
        
        self.buffer = np.zeros((self.render_height, self.render_width, 2, 3), dtype=np.uint8)
        
        editor_width = self.term_width - self.render_width - 1
        if editor_width < 10:
            editor_width = 10
            self.render_width = self.term_width - editor_width - 1
        
        self.editor = TextEditor(
            self.stdscr, 
            self.render_width,
            editor_width, 
            self.term_height
        )
    
    def update_dimensions(self):
        render_width = int(self.term_width * self.split_ratio)
        render_width = max(10, min(render_width, self.term_width - 10))
        
        self.render_width = render_width
        self.render_height = self.term_height
        
        self.gl_width = self.render_width
        self.gl_height = self.render_height * 2
        
        self.buffer = np.zeros((self.render_height, self.render_width, 2, 3), dtype=np.uint8)
    
    def init_color_pairs(self):
        for bg in range(8):
            for fg in range(8):
                pair_idx = bg * 8 + fg + 1
                if pair_idx < 64:
                    curses.init_pair(pair_idx, fg, bg)
    
    def get_closest_color(self, r, g, b):
        r_bin = 1 if r > 127 else 0
        g_bin = 1 if g > 127 else 0
        b_bin = 1 if b > 127 else 0
        return r_bin * 1 + g_bin * 2 + b_bin * 4
    
    def render_to_buffer(self):
        glReadBuffer(GL_BACK)
        pixels = glReadPixels(0, 0, self.gl_width, self.gl_height, GL_RGB, GL_UNSIGNED_BYTE)
        pixel_array = np.frombuffer(pixels, dtype=np.uint8).reshape(self.gl_height, self.gl_width, 3)
        pixel_array = np.flipud(pixel_array)
        
        height_limit = min(self.render_height, pixel_array.shape[0] // 2)
        width_limit = min(self.render_width, pixel_array.shape[1])
        
        for y in range(height_limit):
            for x in range(width_limit):
                self.buffer[y, x, 0] = pixel_array[y*2, x]
                self.buffer[y, x, 1] = pixel_array[y*2+1, x]
                
    def display_error(self, error_message):
        try:
            self.error_message = error_message
            if not error_message:
                return
                
            error_y = self.term_height - 1
            max_len = min(len(error_message), self.render_width)
            
            self.stdscr.attron(curses.color_pair(4 * 8 + 7 + 1))  # Red bg, white fg 
            self.stdscr.addstr(error_y, 0, error_message[:max_len])
            
            if max_len < self.render_width:
                self.stdscr.addstr(error_y, max_len, " " * (self.render_width - max_len))
            
            self.stdscr.attroff(curses.color_pair(4 * 8 + 7 + 1))
        except curses.error:
            pass

    def display_buffer(self):
        term_height, term_width = self.stdscr.getmaxyx()
        if term_height != self.term_height or term_width != self.term_width:
            self.term_height, self.term_width = term_height, term_width
            self.update_dimensions()
        
        max_y = min(self.render_height - 1, term_height - 1
        ) if self.error_message else min(self.render_height, term_height)
        max_x = min(self.render_width, term_width - 1)
        
        for y in range(max_y):
            for x in range(max_x):
                if y < self.buffer.shape[0] and x < self.buffer.shape[1]:
                    top_pix = self.buffer[y, x, 0]
                    bot_pix = self.buffer[y, x, 1]
                    
                    top_color = self.get_closest_color(*top_pix)
                    bot_color = self.get_closest_color(*bot_pix)
                    
                    pair_idx = top_color * 8 + bot_color + 1
                    if pair_idx >= 64: pair_idx = 63

                    self.stdscr.addch(y, x, '▄', curses.color_pair(pair_idx))

        # draw ui
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_time = current_time

        self.stdscr.addstr(3, 0, f"FPS: {self.fps}")
        self.stdscr.addstr(2, 0, f"Zoom: {self.camera_distance:.1f}")
        self.stdscr.addstr(1, 0, f"Angle: {self.camera_rotation_y:.1f}°, {self.camera_rotation_x:.1f}°")
        self.stdscr.addstr(0, 0, "[TAB] Auto Rotate | [M] Rotate/Zoom")

    
    def draw_scene(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glLoadIdentity()
        glTranslatef(self.camera_position_x, self.camera_position_y, -self.camera_distance)
        glRotatef(self.camera_rotation_x, 1.0, 0.0, 0.0)
        glRotatef(self.camera_rotation_y, 0.0, 1.0, 0.0)
        
        try:
            json_data = '\n'.join(self.editor.content)
            if self.auto_rotate:
                self.rotation_angle += 1
                self.last_rotation_angle = self.rotation_angle
            else:
                self.rotation_angle = self.last_rotation_angle
                
            render_success = self.model_renderer.render(json_data, self.rotation_angle)
            if not render_success:
                self.display_error(self.model_renderer.error_message)
            else:
                self.display_error("")
        except Exception as e:
            self.display_error(str(e))
        
        pygame.display.flip()
    
    def on_mouse_event(self, event):
        _, x, y, _, button_state = event
        
        if x >= self.render_width:
            return False
        
        # rotate TODO: fix
        if button_state & curses.BUTTON1_PRESSED:
            if not self.left_dragging:
                self.left_dragging = True
                self.last_mouse_x, self.last_mouse_y = x, y
            else:
                dx, dy = x - self.last_mouse_x, y - self.last_mouse_y
                
                if dx != 0 or dy != 0:
                    self.auto_rotate = False
                    self.camera_rotation_y += dx * 0.5 * self.mouse_sensitivity
                    self.camera_rotation_x += dy * 0.5 * self.mouse_sensitivity
                    self.last_mouse_x, self.last_mouse_y = x, y
            return True
        elif button_state & curses.BUTTON1_RELEASED:
            self.left_dragging = False
            return True
        
        # panning
        elif button_state & curses.BUTTON3_PRESSED:
            if not self.right_dragging:
                self.right_dragging = True
                self.last_mouse_x, self.last_mouse_y = x, y
            else:
                dx, dy = x - self.last_mouse_x, y - self.last_mouse_y
                
                if dx != 0 or dy != 0:
                    self.camera_position_x += dx * 0.01 * self.mouse_sensitivity
                    self.camera_position_y -= dy * 0.01 * self.mouse_sensitivity
                    self.last_mouse_x, self.last_mouse_y = x, y
            return True
        elif button_state & curses.BUTTON3_RELEASED:
            self.right_dragging = False
            return True
        
        # zoom
        elif button_state & curses.BUTTON4_PRESSED:
            self.camera_distance = max(1.0, self.camera_distance - 0.3)
            return True
        elif button_state & curses.BUTTON5_PRESSED:
            self.camera_distance += 0.3
            return True
        
        # motion
        elif self.left_dragging or self.right_dragging:
            dx, dy = x - self.last_mouse_x, y - self.last_mouse_y
            if dx != 0 or dy != 0:
                if self.left_dragging:
                    self.auto_rotate = False
                    self.camera_rotation_y += dx * 0.5 * self.mouse_sensitivity
                    self.camera_rotation_x += dy * 0.5 * self.mouse_sensitivity
                else:  # right_dragging
                    self.camera_position_x += dx * 0.01 * self.mouse_sensitivity
                    self.camera_position_y -= dy * 0.01 * self.mouse_sensitivity
                self.last_mouse_x, self.last_mouse_y = x, y
            return True
        
        return True
    
    def on_key_event(self):
        key = self.stdscr.getch()
        # 9 = tab | 19 = ctrl+s
        if key == 9:    self.auto_rotate = not self.auto_rotate
        elif key == 19: self.editor.save_file()
        elif key == curses.KEY_MOUSE:
            mouse_event = curses.getmouse()
            if not self.on_mouse_event(mouse_event):
                self.editor.handle_key(key)

        elif key != -1: self.editor.handle_key(key)
    
    def render(self):
        self.setup_screen()
            
        while True:
            self.on_key_event()
            self.editor.check_file_changed()
                
            self.draw_scene()
            self.render_to_buffer()
            self.display_buffer()
            self.editor.draw()
                
            self.stdscr.refresh()
            time.sleep(0.016) 


renderer = TerminalRenderer()
renderer.render()