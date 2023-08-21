class Comparator(object):
    def __init__(self, left, right, print=lambda x: x.strip(), strip=lambda x: x.strip(), single_match=False, **args):
        self.name = right
        self.left = left
        self.right = right
        self.single_match = single_match
        self.print = print
        self.left_print = args.get('left_print', False) or print
        self.right_print = args.get('right_print', False) or print
        self.left_strip = args.get('left_strip', False) or strip
        self.right_strip = args.get('right_strip', False) or strip
