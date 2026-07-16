import pygame
import os
import copy

# -------------------- Config --------------------
BOARD_PIX = 640
PANEL_PIX = 260
WIDTH, HEIGHT = BOARD_PIX + PANEL_PIX, 700
ROWS, COLS = 8, 8
SQUARE_SIZE = BOARD_PIX // COLS

# Colors
WHITE = (232, 235, 239)
GRAY = (125, 135, 150)
RED = (255, 100, 100)
TRANSLUCENT_GRAY = (60, 60, 60, 140)
TEXT_COLOR = (10, 10, 10)
PANEL_BG = (240, 240, 240)
BTN_BG = (210, 210, 210)
BTN_BORDER = (120, 120, 120)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess (with en passant, checks, history)")
font = pygame.font.SysFont("Arial", 18)
bigfont = pygame.font.SysFont("Arial", 22, bold=True)

# -------------------- Images --------------------
PIECES = {}
def load_images():
    pieces = ['bp', 'br', 'bn', 'bb', 'bq', 'bk',
              'wp', 'wr', 'wn', 'wb', 'wq', 'wk']
    for piece in pieces:
        path = os.path.join("images", piece + ".png")
        image = pygame.image.load(path)
        PIECES[piece] = pygame.transform.scale(image, (SQUARE_SIZE, SQUARE_SIZE))

# -------------------- Board --------------------
def create_board():
    return [
        ['br', 'bn', 'bb', 'bq', 'bk', 'bb', 'bn', 'br'],
        ['bp'] * 8,
        [''] * 8,
        [''] * 8,
        [''] * 8,
        [''] * 8,
        ['wp'] * 8,
        ['wr', 'wn', 'wb', 'wq', 'wk', 'wb', 'wn', 'wr']
    ]

def create_castling_rights():
    return {"wK": True, "wQ": True, "bK": True, "bQ": True}

# -------------------- Utilities --------------------
def draw_board():
    for row in range(ROWS):
        for col in range(COLS):
            color = WHITE if (row + col) % 2 == 0 else GRAY
            pygame.draw.rect(screen, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

def draw_pieces(board):
    for row in range(ROWS):
        for col in range(COLS):
            piece = board[row][col]
            if piece != '':
                screen.blit(PIECES[piece], (col * SQUARE_SIZE, row * SQUARE_SIZE))

def get_square_under_mouse(pos):
    x, y = pos
    if x >= BOARD_PIX or y >= BOARD_PIX:
        return None, None
    return y // SQUARE_SIZE, x // SQUARE_SIZE

def square_to_notation(r, c):
    return chr(ord('a') + c) + str(8 - r)

def is_enemy(piece1, piece2):
    return piece1 and piece2 and piece1[0] != piece2[0]

def find_king(board, color):
    k = color + 'k'
    for r in range(8):
        for c in range(8):
            if board[r][c] == k:
                return r, c
    return None

# -------------------- Move generation (includes captures & en passant & castling) --------------------
def gen_pseudo_legal_moves(board, piece, r, c, castling_rights, en_passant_target):
    """
    Generate pseudo-legal moves for a piece at (r,c).
    Pseudo-legal: does not filter moves that leave king in check.
    en_passant_target: tuple (r,c) that can be captured en-passant, or None.
    """
    moves = []
    color = piece[0]
    kind = piece[1]

    directions = []
    if kind == 'p':
        direction = -1 if color == 'w' else 1
        start_row = 6 if color == 'w' else 1
        # forward one
        if 0 <= r + direction < 8 and board[r + direction][c] == '':
            moves.append((r + direction, c, False))  # normal move
            # two-step
            if r == start_row and board[r + 2*direction][c] == '':
                moves.append((r + 2*direction, c, False))
        # captures
        for dc in (-1, 1):
            rr, cc = r + direction, c + dc
            if 0 <= rr < 8 and 0 <= cc < 8:
                if is_enemy(piece, board[rr][cc]):
                    moves.append((rr, cc, True))  # capture
        # en passant capture
        if en_passant_target:
            ep_r, ep_c = en_passant_target
            # en_passant_target is square behind pawn that double-moved; capture is to that square
            # For a pawn at r,c, the target must be on same rank as the capture destination:
            # white pawn must be at rank 3 (r=3) and ep target at (2, c+/-1) when capturing black pawn that moved from 1->3
            # simpler: if ep square equals r+direction, c+dc, then add en-passant capture
            for dc in (-1, 1):
                rr, cc = r + direction, c + dc
                if (rr, cc) == (ep_r, ep_c):
                    moves.append((rr, cc, True, 'ep'))  # en-passant marker
    elif kind == 'n':
        deltas = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                  (1, -2), (1, 2), (2, -1), (2, 1)]
        for dr, dc in deltas:
            rr, cc = r + dr, c + dc
            if 0 <= rr < 8 and 0 <= cc < 8 and (board[rr][cc] == '' or is_enemy(piece, board[rr][cc])):
                moves.append((rr, cc, board[rr][cc] != ''))
    elif kind == 'b':
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    elif kind == 'r':
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    elif kind == 'q':
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1),
                      (-1, -1), (-1, 1), (1, -1), (1, 1)]
    elif kind == 'k':
        deltas = [(-1, -1), (-1, 0), (-1, 1),
                  (0, -1), (0, 1),
                  (1, -1), (1, 0), (1, 1)]
        for dr, dc in deltas:
            rr, cc = r + dr, c + dc
            if 0 <= rr < 8 and 0 <= cc < 8:
                if board[rr][cc] == '' or is_enemy(piece, board[rr][cc]):
                    moves.append((rr, cc, board[rr][cc] != ''))
        # castling (only basic checks: king/rook unmoved and path empty)
        if color == 'w' and r == 7 and c == 4:
            if castling_rights["wK"] and board[7][5] == '' and board[7][6] == '':
                moves.append((7, 6, False, 'O-O'))
            if castling_rights["wQ"] and board[7][3] == '' and board[7][2] == '' and board[7][1] == '':
                moves.append((7, 2, False, 'O-O-O'))
        if color == 'b' and r == 0 and c == 4:
            if castling_rights["bK"] and board[0][5] == '' and board[0][6] == '':
                moves.append((0, 6, False, 'O-O'))
            if castling_rights["bQ"] and board[0][3] == '' and board[0][2] == '' and board[0][1] == '':
                moves.append((0, 2, False, 'O-O-O'))
    # sliding pieces
    for dr, dc in directions:
        rr, cc = r + dr, c + dc
        while 0 <= rr < 8 and 0 <= cc < 8:
            if board[rr][cc] != '':
                if is_enemy(piece, board[rr][cc]):
                    moves.append((rr, cc, True))
                break
            moves.append((rr, cc, False))
            rr += dr
            cc += dc
    # Normalize move tuple forms into (r,c,meta...) where meta could be capture flag or special marker
    # We will keep heterogeneous tuples: (r,c,...) handled by calling code
    return moves

# -------------------- Helpers for check detection and making moves safely --------------------
def make_move_on_board(board, move, old_r, old_c, en_passant_target, castling_rights):
    """
    Apply a move tuple onto a copy of board and return new_board, new_en_passant_target, new_castling_rights, captured_piece_info.
    move can be: (nr,nc,...) where optional last element may be 'ep' or 'O-O'/'O-O-O'.
    captured_piece_info: (r,c,piece) if capture happened (including en-passant capture removal location)
    """
    new_board = copy.deepcopy(board)
    nr, nc = move[0], move[1]
    meta = move[2:] if len(move) > 2 else []
    piece = new_board[old_r][old_c]
    captured = None
    new_en_passant = None
    new_castling = copy.deepcopy(castling_rights)

    # en passant: capture the pawn that moved two steps previously (the pawn sits on same file on old rank)
    if 'ep' in meta:
        # captured pawn is on same file as target but on old_r (the pawn that moved 2 squares)
        cap_r = old_r  # pawn being captured is on the same row as the capturing pawn originally (because capture goes diagonally forward)
        cap_c = nc
        captured = (cap_r, cap_c, new_board[cap_r][cap_c])
        new_board[cap_r][cap_c] = ''
    elif new_board[nr][nc] != '':
        captured = (nr, nc, new_board[nr][nc])

    # Perform the move
    new_board[nr][nc] = piece
    new_board[old_r][old_c] = ''

    # Castling rook move if needed
    if meta and meta[0] in ('O-O', 'O-O-O'):
        if piece == 'wk':
            if meta[0] == 'O-O':
                new_board[7][5] = 'wr'
                new_board[7][7] = ''
            else:
                new_board[7][3] = 'wr'
                new_board[7][0] = ''
        elif piece == 'bk':
            if meta[0] == 'O-O':
                new_board[0][5] = 'br'
                new_board[0][7] = ''
            else:
                new_board[0][3] = 'br'
                new_board[0][0] = ''

    # Update castling rights if king or rook moved or rook captured
    if piece == 'wk':
        new_castling["wK"] = new_castling["wQ"] = False
    if piece == 'bk':
        new_castling["bK"] = new_castling["bQ"] = False
    if piece == 'wr':
        if old_r == 7 and old_c == 0:
            new_castling["wQ"] = False
        if old_r == 7 and old_c == 7:
            new_castling["wK"] = False
    if piece == 'br':
        if old_r == 0 and old_c == 0:
            new_castling["bQ"] = False
        if old_r == 0 and old_c == 7:
            new_castling["bK"] = False
    # If a rook was captured, adjust rights
    if captured and captured[2] in ('wr', 'br'):
        cap_piece = captured[2]
        if cap_piece == 'wr' and captured[0] == 7 and captured[1] == 0:
            new_castling["wQ"] = False
        if cap_piece == 'wr' and captured[0] == 7 and captured[1] == 7:
            new_castling["wK"] = False
        if cap_piece == 'br' and captured[0] == 0 and captured[1] == 0:
            new_castling["bQ"] = False
        if cap_piece == 'br' and captured[0] == 0 and captured[1] == 7:
            new_castling["bK"] = False

    # Set new en_passant_target: if pawn moved two squares, set the behind-square as target
    if piece[1] == 'p' and abs(nr - old_r) == 2:
        # the target square that can be captured to is the square the pawn passed over
        passed_over_r = (nr + old_r) // 2
        new_en_passant = (passed_over_r, nc)
    else:
        new_en_passant = None

    return new_board, new_en_passant, new_castling, captured

def is_in_check(board, color, castling_rights, en_passant_target):
    """
    Determine if color's king is in check on the given board.
    """
    kr = find_king(board, color)
    if kr is None:
        return True  # missing king => treat as in check
    kr_r, kr_c = kr
    opp_color = 'b' if color == 'w' else 'w'
    # generate all opponent pseudo-legal moves and see if any lands on king
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece != '' and piece[0] == opp_color:
                moves = gen_pseudo_legal_moves(board, piece, r, c, castling_rights, en_passant_target)
                for mv in moves:
                    if mv[0] == kr_r and mv[1] == kr_c:
                        return True
    return False

def gen_legal_moves_filtered(board, r, c, castling_rights, en_passant_target):
    """
    From square r,c generate legal moves that do not leave own king in check.
    Returns list of tuples (nr,nc, meta...)
    """
    piece = board[r][c]
    if piece == '':
        return []
    pseudo = gen_pseudo_legal_moves(board, piece, r, c, castling_rights, en_passant_target)
    legal = []
    for mv in pseudo:
        # apply move on a copy and check if own king is in check afterwards
        new_b, new_ep, new_cast, captured = make_move_on_board(board, mv, r, c, en_passant_target, castling_rights)
        # If the move was en-passant, note that that capture removed pawn; make_move_on_board handles that.
        if not is_in_check(new_b, piece[0], new_cast, new_ep):
            legal.append(mv)
    return legal

# -------------------- Move notation --------------------
def notation_from_move(piece, old_r, old_c, mv, captured, gives_check):
    """
    produce a simple move string:
    - castling: O-O or O-O-O
    - pawn moves: e2e4 or exd3 (ep)
    - others: e1e2 or Nf3 (we'll stick to from-to to keep implementation simple)
    append + if gives_check
    """
    meta = mv[2:] if len(mv) > 2 else []
    if meta and meta[0] in ('O-O', 'O-O-O'):
        s = meta[0]
    else:
        src = square_to_notation(old_r, old_c)
        dst = square_to_notation(mv[0], mv[1])
        if piece[1] == 'p':
            if captured:
                # show capture with file
                s = src[0] + 'x' + dst
                if 'ep' in meta:
                    s += ' (ep)'
            else:
                s = src + dst
        else:
            if captured:
                s = src + 'x' + dst
            else:
                s = src + dst
    if gives_check:
        s += '+'
    return s

# -------------------- History & UI --------------------
def draw_move_highlight(r, c):
    s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
    pygame.draw.circle(s, TRANSLUCENT_GRAY, (SQUARE_SIZE // 2, SQUARE_SIZE // 2), SQUARE_SIZE // 6)
    screen.blit(s, (c * SQUARE_SIZE, r * SQUARE_SIZE))

def draw_panel(move_list, history_index, turn):
    # panel background
    pygame.draw.rect(screen, PANEL_BG, (BOARD_PIX, 0, PANEL_PIX, HEIGHT))
    # Title
    title = bigfont.render("Moves", True, TEXT_COLOR)
    screen.blit(title, (BOARD_PIX + 12, 8))
    # Moves list (two-column style: move number + white move / black move)
    y = 45
    # Show as many entries as fit
    per_page = 24
    # Determine starting index for scrolling: show latest entries if many
    start = max(0, len(move_list) - per_page)
    for i in range(start, len(move_list)):
        move_num = i + 1
        text = f"{move_num}. {move_list[i]}"
        lbl = font.render(text, True, TEXT_COLOR)
        screen.blit(lbl, (BOARD_PIX + 12, y))
        y += 22
    # Buttons Prev / Next
    prev_btn = pygame.Rect(BOARD_PIX + 30, HEIGHT - 80, 80, 36)
    next_btn = pygame.Rect(BOARD_PIX + 130, HEIGHT - 80, 80, 36)
    pygame.draw.rect(screen, BTN_BG, prev_btn)
    pygame.draw.rect(screen, BTN_BG, next_btn)
    pygame.draw.rect(screen, BTN_BORDER, prev_btn, 2)
    pygame.draw.rect(screen, BTN_BORDER, next_btn, 2)
    ptxt = font.render("Prev", True, TEXT_COLOR)
    ntxt = font.render("Next", True, TEXT_COLOR)
    screen.blit(ptxt, (prev_btn.x + 22, prev_btn.y + 8))
    screen.blit(ntxt, (next_btn.x + 22, next_btn.y + 8))
    # Turn indicator
    ttxt = font.render(f"Turn: {'White' if turn == 'w' else 'Black'}", True, TEXT_COLOR)
    screen.blit(ttxt, (BOARD_PIX + 12, HEIGHT - 120))
    # Info if viewing history
    if history_index != len(history_states) - 1:
        info = font.render("Viewing past position", True, (150, 20, 20))
        screen.blit(info, (BOARD_PIX + 12, HEIGHT - 150))
    return prev_btn, next_btn

# -------------------- Game state --------------------
board = create_board()
castling_rights = create_castling_rights()
en_passant_target = None  # square (r,c) that may be captured en-passant (only valid immediately after double pawn move)
turn = 'w'

# History: store tuples of (board, castling_rights, en_passant_target, move_str)
history_states = []  # will contain board states (deep copies)
history_moves = []   # corresponding moves notation
history_index = -1   # index into history_states (for stepping through). -1 means not initialized
# We will append initial position as history_states[0]
history_states.append(copy.deepcopy(board))
history_history_castling = [copy.deepcopy(castling_rights)]
history_enpassant_list = [en_passant_target]
history_moves.append("start")
history_index = 0

load_images()

selected_piece = None
selected_pos = None
legal_moves = []
dragging = False

running = True
clock = pygame.time.Clock()
while running:
    clock.tick(60)
    screen.fill((200, 200, 200))
    draw_board()

    # Draw highlights
    for mv in legal_moves:
        draw_move_highlight(mv[0], mv[1])

    # selected outline
    if selected_pos:
        sr, sc = selected_pos
        pygame.draw.rect(screen, RED, (sc * SQUARE_SIZE, sr * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 3)

    draw_pieces(board)

    # Draw right panel and buttons
    prev_btn, next_btn = draw_panel(history_moves[1:], history_index - 1, turn)  # show moves (exclude "start")

    # dragged sprite
    if dragging and selected_piece:
        mx, my = pygame.mouse.get_pos()
        # only draw if over board
        if mx < BOARD_PIX and my < BOARD_PIX:
            screen.blit(PIECES[selected_piece], (mx - SQUARE_SIZE//2, my - SQUARE_SIZE//2))

    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            # check panel buttons
            if BOARD_PIX <= mx < WIDTH:
                # inside panel area: check Prev/Next buttons
                if prev_btn.collidepoint(mx, my):
                    # go back one
                    if history_index > 0:
                        history_index -= 1
                        # load state at history_index
                        board = copy.deepcopy(history_states[history_index])
                        castling_rights = copy.deepcopy(history_history_castling[history_index])
                        en_passant_target = history_enpassant_list[history_index]
                        # the turn also must be deduced: white starts at index 0; after each full move we swapped turn
                        # We'll deduce by history index parity: initial start index 0 is white to move
                        # But we stored positions after moves; so set turn accordingly:
                        turn = 'w' if history_index % 2 == 0 else 'b'
                if next_btn.collidepoint(mx, my):
                    # go forward one (but not beyond latest)
                    if history_index < len(history_states) - 1:
                        history_index += 1
                        board = copy.deepcopy(history_states[history_index])
                        castling_rights = copy.deepcopy(history_history_castling[history_index])
                        en_passant_target = history_enpassant_list[history_index]
                        turn = 'w' if history_index % 2 == 0 else 'b'
                continue

            # clicking on board area
            row, col = get_square_under_mouse((mx, my))
            if row is None:
                continue
            # If viewing past (not latest), disallow selecting/moving
            if history_index != len(history_states) - 1:
                # ignore board clicks while viewing history
                continue
            piece = board[row][col]
            if piece != '' and piece[0] == turn:
                # initialize selection
                selected_piece = piece
                selected_pos = (row, col)
                legal_moves = gen_legal_moves_filtered(board, row, col, castling_rights, en_passant_target)
                dragging = True
            else:
                selected_piece = None
                selected_pos = None
                legal_moves = []
                dragging = False

        elif event.type == pygame.MOUSEBUTTONUP:
            mx, my = pygame.mouse.get_pos()
            row, col = get_square_under_mouse((mx, my))
            if selected_piece and selected_pos and row is not None and history_index == len(history_states) - 1:
                old_r, old_c = selected_pos
                chosen = None
                for mv in legal_moves:
                    if mv[0] == row and mv[1] == col:
                        chosen = mv
                        break
                if chosen:
                    # Apply move
                    new_board, new_enp, new_cast, captured = make_move_on_board(board, chosen, old_r, old_c, en_passant_target, castling_rights)
                    # determine if move gives check
                    opponent = 'b' if turn == 'w' else 'w'
                    gives_check = is_in_check(new_board, opponent, new_cast, new_enp)
                    # notation
                    move_str = notation_from_move(selected_piece, old_r, old_c, chosen, captured, gives_check)
                    # commit new state
                    board = new_board
                    en_passant_target = new_enp
                    castling_rights = new_cast
                    # advance history (append)
                    history_states.append(copy.deepcopy(board))
                    history_history_castling.append(copy.deepcopy(castling_rights))
                    history_enpassant_list.append(en_passant_target)
                    history_moves.append(move_str)
                    history_index = len(history_states) - 1
                    # swap turn
                    turn = opponent
                # clear selection regardless
            selected_piece = None
            selected_pos = None
            legal_moves = []
            dragging = False

pygame.quit()
