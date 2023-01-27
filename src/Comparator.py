class Comparator(object):
    def __init__(self, left, right, print=lambda x: x, single_match=False, **args):
        self.name = right
        self.left = left
        self.right = right
        self.single_match = single_match
        self.print = print
        self.left_strip = args.get('left_strip', False) or args.get('strip', False)
        self.right_strip = args.get('right_strip', False) or args.get('strip', False)
        if not (args.get('strip', False) or (args.get('left_strip', False) and args.get('right_strip', False))):
            raise Exception('Provide proper strip functions.')
