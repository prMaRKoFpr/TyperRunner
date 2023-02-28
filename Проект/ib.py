import pygame as pygame


pygame.init()

screen = pygame.display.set_mode((640, 480))


class InputBox:

    def __init__(self, screen, x, y, w, h, text=''):
        self.screen = screen
        self.rect = pygame.Rect(x, y, w, h)
        self.FONT = pygame.font.Font(None, 52)
        self.COLOR_INACTIVE = 'black'
        self.COLOR_ACTIVE =   'grey'
        self.color =          'black'
        self.text = text
        self.txt_surface = self.FONT.render(text, True, self.color)
        self.active = False
        self.value_changed = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.rect.collidepoint(event.pos):
                # Toggle the active variable.
                self.active = not self.active
                self.text = ''
                self._set_value()
            else:
                self.active = False
                self._check_value()
                self._set_value()
            # Change the current color of the input box.
            self.color = self.COLOR_ACTIVE if self.active else self.COLOR_INACTIVE
        if event.type == pygame.KEYDOWN:
            if self.active:
                # if event.key == pygame.K_RETURN:
                #     print(self.text)
                #     self.text = ''
                if event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    if event.unicode.isdigit():
                        self.text += event.unicode
                # Re-render the text.
                self._set_value()

    def get_text(self):
        return self.text

    def _set_value(self):
        self.txt_surface = self.FONT.render(self.text, True, self.color)

    def _check_value(self):
        if self.text == '':
            self.text = '32'
        if int(self.text) < 8:
            self.text = '8'
        elif int(self.text) > 65:
            self.text = '65'
        self.value_changed = True

    def update(self):
        # Resize the box if the text is too long.
        width = max(200, self.txt_surface.get_width()+10)
        self.rect.w = width

    def draw(self, screen):
        # Blit the text.
        screen.blit(self.txt_surface, (self.rect.x+10, self.rect.y+30))
        # Blit the rect.
        pygame.draw.rect(screen, self.color, self.rect, 2)



def main():
    clock = pygame.time.Clock()
    input_box1 = InputBox(screen, 100, 100, 140, 32)
    input_box2 = InputBox(screen, 100, 300, 140, 32)
    input_boxes = [input_box1, input_box2]
    done = False

    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            for box in input_boxes:
                box.handle_event(event)

        # for box in input_boxes:
        #     box.update()

        screen.fill((30, 30, 30))
        for box in input_boxes:
            box.draw(screen)

        pygame.display.flip()
        clock.tick(30)


if __name__ == '__main__':
    main()
    pygame.quit()
