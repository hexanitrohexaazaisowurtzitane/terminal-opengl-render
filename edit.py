import curses
import os
import json
import time
from OpenGL.GL import *


class TextEditor:
    def __init__(self, stdscr, start_x, width, height):
        self.stdscr = stdscr
        self.start_x = start_x
        self.width = width
        self.height = height
        self.content = []
        self.cursor_y = self.cursor_x = self.scroll_y = 0
        self.filename = "model.json"
        self.status_message = ""
        self.status_time = self.last_mod_time = 0
        
        self.load_file()
    
    def load_file(self):
        with open("model.json", 'r') as f:
            self.content = f.read().split('\n')
        self.last_mod_time = os.path.getmtime("model.json")
        self.set_status(f"loaded model from file")
    
    def save_file(self):
        with open(self.filename, 'w') as f:
            f.write('\n'.join(self.content))
        self.last_mod_time = os.path.getmtime(self.filename)
        self.set_status(f"saved model to file")
        return True
    
    def check_file_changed(self):
        mod_time = os.path.getmtime(self.filename)
        if mod_time > self.last_mod_time:
            self.load_file()
            return True
    
    def set_status(self, message):
        self.status_message = message
        self.status_time = time.time()
    
    def handle_key(self, key):
        if key == curses.KEY_UP:
            if self.cursor_y > 0:
                self.cursor_y -= 1
                if self.cursor_x > len(self.content[self.cursor_y]):
                    self.cursor_x = len(self.content[self.cursor_y])
        elif key == curses.KEY_DOWN:
            if self.cursor_y < len(self.content) - 1:
                self.cursor_y += 1
                if self.cursor_x > len(self.content[self.cursor_y]):
                    self.cursor_x = len(self.content[self.cursor_y])
        elif key == curses.KEY_LEFT:
            if self.cursor_x > 0:
                self.cursor_x -= 1
            elif self.cursor_y > 0:
                self.cursor_y -= 1
                self.cursor_x = len(self.content[self.cursor_y])
        elif key == curses.KEY_RIGHT:
            if self.cursor_x < len(self.content[self.cursor_y]):
                self.cursor_x += 1
            elif self.cursor_y < len(self.content) - 1:
                self.cursor_y += 1
                self.cursor_x = 0
        elif key in (curses.KEY_BACKSPACE, 8, 127):
            if self.cursor_x > 0:
                self.content[self.cursor_y] = (
                    self.content[self.cursor_y][:self.cursor_x-1] + 
                    self.content[self.cursor_y][self.cursor_x:]
                )
                self.cursor_x -= 1
            elif self.cursor_y > 0:
                prev_line_len = len(self.content[self.cursor_y-1])
                self.content[self.cursor_y-1] += self.content[self.cursor_y]
                self.content.pop(self.cursor_y)
                self.cursor_y -= 1
                self.cursor_x = prev_line_len
        elif key == curses.KEY_DC:
            if self.cursor_x < len(self.content[self.cursor_y]):
                self.content[self.cursor_y] = (
                    self.content[self.cursor_y][:self.cursor_x] + 
                    self.content[self.cursor_y][self.cursor_x+1:]
                )
            elif self.cursor_y < len(self.content) - 1:
                self.content[self.cursor_y] += self.content[self.cursor_y+1]
                self.content.pop(self.cursor_y+1)
        elif key == curses.KEY_HOME:
            self.cursor_x = 0
        elif key == curses.KEY_END:
            self.cursor_x = len(self.content[self.cursor_y])
        elif key == curses.KEY_PPAGE:
            self.cursor_y = max(0, self.cursor_y - (self.height - 2))
            self.scroll_y = max(0, self.scroll_y - (self.height - 2))
            if self.cursor_x > len(self.content[self.cursor_y]):
                self.cursor_x = len(self.content[self.cursor_y])
        elif key == curses.KEY_NPAGE:
            self.cursor_y = min(len(self.content) - 1, self.cursor_y + (self.height - 2))
            if self.cursor_y >= self.scroll_y + (self.height - 2):
                self.scroll_y = max(0, self.cursor_y - (self.height - 3))
            if self.cursor_x > len(self.content[self.cursor_y]):
                self.cursor_x = len(self.content[self.cursor_y])
        elif key in (10, 13): # ent
            new_line = self.content[self.cursor_y][self.cursor_x:]
            self.content[self.cursor_y] = self.content[self.cursor_y][:self.cursor_x]
            self.content.insert(self.cursor_y + 1, new_line)
            self.cursor_y += 1
            self.cursor_x = 0
        elif key == 19:  return self.save_file()
        elif 32 <= key <= 126:  # printable
            try:
                char = chr(key)
                self.content[self.cursor_y] = (
                    self.content[self.cursor_y][:self.cursor_x] + 
                    char + 
                    self.content[self.cursor_y][self.cursor_x:]
                )
                self.cursor_x += 1
            except Exception as e:
                self.set_status(str(e))
        
        # update scroll if cursor out
        if self.cursor_y < self.scroll_y:
            self.scroll_y = self.cursor_y
        elif self.cursor_y >= self.scroll_y + self.height - 2:
            self.scroll_y = max(0, self.cursor_y - self.height + 3)
        
        return False
            
    def draw(self):
        # slider
        for i in range(self.height):
            try:
                self.stdscr.addstr(i, self.start_x, "│")
            except curses.error:
                pass
        

        display_height = self.height - 1
        for i in range(display_height):
            try:
                self.stdscr.addstr(i, self.start_x + 1, " " * (self.width - 1))
            except curses.error:
                pass
                
            line_num = i + self.scroll_y
            if 0 <= line_num < len(self.content):
                line = self.content[line_num]
                max_width = min(self.width - 1, curses.COLS - self.start_x - 2)
                displayed_line = line[:max_width - 1] + "…" if len(line) > max_width else line
                    
                try:
                    self.stdscr.addstr(i, self.start_x + 1, displayed_line)
                except curses.error:
                    pass
                
                # highlight
                if line_num == self.cursor_y:
                    try:
                        self.stdscr.chgat(i, self.start_x + 1, min(len(displayed_line), max_width), 
                                        curses.A_REVERSE)
                                        
                        # cur char TODO
                        if self.cursor_x < len(displayed_line):
                            try:
                                curses.init_pair(100, curses.COLOR_WHITE, curses.COLOR_BLACK)
                                char_to_highlight = displayed_line[self.cursor_x:self.cursor_x+1]
                                self.stdscr.addstr(i, self.start_x + 1 + self.cursor_x, char_to_highlight, 
                                                curses.color_pair(100) | curses.A_REVERSE | curses.A_BOLD)
                            except curses.error:
                                pass
                    except curses.error:
                        pass
        
        # statuus
        if time.time() - self.status_time < 3:
            status_y = min(self.height - 1, curses.LINES - 1)
            status_x = self.start_x + 1
            try:
                max_width = min(self.width - 1, curses.COLS - status_x - 1)
                self.stdscr.addstr(status_y, status_x, self.status_message[:max_width])
            except curses.error:
                pass
        
        # point cursor
        cursor_screen_y = self.cursor_y - self.scroll_y
        cursor_screen_x = self.start_x + 1 + min(self.cursor_x, curses.COLS - self.start_x - 2)
        
        if 0 <= cursor_screen_y < min(self.height - 1, curses.LINES
        ) and 0 <= cursor_screen_x < curses.COLS:
            self.stdscr.move(cursor_screen_y, cursor_screen_x)


class JsonModelRenderer:
    def __init__(self):
        self.gl_modes = {
            "GL_POINTS": GL_POINTS,
            "GL_LINES": GL_LINES,
            "GL_LINE_STRIP": GL_LINE_STRIP,
            "GL_LINE_LOOP": GL_LINE_LOOP,
            "GL_TRIANGLES": GL_TRIANGLES,
            "GL_TRIANGLE_STRIP": GL_TRIANGLE_STRIP,
            "GL_TRIANGLE_FAN": GL_TRIANGLE_FAN,
            "GL_QUADS": GL_QUADS,
            "GL_QUAD_STRIP": GL_QUAD_STRIP,
            "GL_POLYGON": GL_POLYGON
        }
        
        self.gl_commands = {
            "rotate3f": glRotatef,
            "translate3f": glTranslatef,
            "scale3f": glScalef,
            "begin": self._begin,
            "end": glEnd,
            "vertex3f": glVertex3f,
            "color3f": glColor3f,
            "normal3f": glNormal3f
        }
        
        self.last_model_hash = None
        self.compiled_model = None
        self.error_message = ""
        self.last_valid_model = {"instructions": []}
        self.last_valid_json = json.dumps(self.last_valid_model)
    
    def _begin(self, mode_str):
        glBegin(self.gl_modes.get(mode_str, GL_TRIANGLES))
    
    def render(self, json_data, angle=0.0):
        current_hash = hash(json_data)
        
        # use compiled
        if current_hash == self.last_model_hash and self.compiled_model:
            glPushMatrix()
            glRotatef(angle, 0.0, 1.0, 0.0)
            self.execute(self.compiled_model)
            glPopMatrix()
            return True
        
        try:
            model = json.loads(json_data)
            instructions = model.get("instructions", [])
            
            # update model n hash
            self.compiled_model = instructions
            self.last_model_hash = current_hash
            self.error_message = ""
            
            self.last_valid_model = model
            self.last_valid_json = json_data
            



            # execute
            glPushMatrix()
            glRotatef(angle, 0.0, 1.0, 0.0)
            self.execute(instructions)
            glPopMatrix()
            
            return True

        except json.JSONDecodeError as je: self.error_message = str(je)
        except Exception            as e:  self.error_message = str(e )
        # use last valid
        

        if self.compiled_model:
            glPushMatrix()
            glRotatef(angle, 0.0, 1.0, 0.0)
            self.execute(self.compiled_model)
            glPopMatrix()
            return False  # false = err
            
        return False



    def execute(self, instructions):
        for instruction in instructions:
            command = instruction.get("command")
            args = instruction.get("args", [])
            
            if command in self.gl_commands:

                if command == "begin" and args:
                    self.gl_commands[command](args[0])
                else:
                    self.gl_commands[command](*args)