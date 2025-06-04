import tkinter as tk
from tkinter import ttk, messagebox

class FakeSNS:
    def __init__(self, root):
        self.root = root
        self.root.title("작가용 가짜 SNS")
        self.posts = []  # Each post is a dict: {"text": str, "comments": [str]}

        self.frame_posts = ttk.Frame(root, padding=10)
        self.frame_posts.pack(fill='both', expand=True)

        # Posts list
        self.posts_listbox = tk.Listbox(self.frame_posts, height=10)
        self.posts_listbox.pack(fill='both', expand=True, side='left')
        self.posts_listbox.bind('<<ListboxSelect>>', self.on_post_select)

        self.scrollbar_posts = ttk.Scrollbar(self.frame_posts, orient='vertical', command=self.posts_listbox.yview)
        self.scrollbar_posts.pack(side='left', fill='y')
        self.posts_listbox.config(yscrollcommand=self.scrollbar_posts.set)

        # Comments frame
        self.frame_comments = ttk.Frame(root, padding=10)
        self.frame_comments.pack(fill='both', expand=True)

        ttk.Label(self.frame_comments, text='댓글 목록').pack(anchor='w')
        self.comments_listbox = tk.Listbox(self.frame_comments, height=8)
        self.comments_listbox.pack(fill='both', expand=True, side='left')
        self.scrollbar_comments = ttk.Scrollbar(self.frame_comments, orient='vertical', command=self.comments_listbox.yview)
        self.scrollbar_comments.pack(side='left', fill='y')
        self.comments_listbox.config(yscrollcommand=self.scrollbar_comments.set)

        # Entry for new post
        self.frame_new_post = ttk.Frame(root, padding=10)
        self.frame_new_post.pack(fill='x')
        ttk.Label(self.frame_new_post, text='새 게시글:').pack(anchor='w')
        self.entry_post = tk.Text(self.frame_new_post, height=3)
        self.entry_post.pack(fill='x', expand=True)
        ttk.Button(self.frame_new_post, text='게시', command=self.add_post).pack(anchor='e', pady=5)

        # Entry for new comment
        self.frame_new_comment = ttk.Frame(root, padding=10)
        self.frame_new_comment.pack(fill='x')
        ttk.Label(self.frame_new_comment, text='새 댓글:').pack(anchor='w')
        self.entry_comment = tk.Entry(self.frame_new_comment)
        self.entry_comment.pack(fill='x', expand=True, side='left')
        ttk.Button(self.frame_new_comment, text='댓글 달기', command=self.add_comment).pack(side='left', padx=5)

    def add_post(self):
        text = self.entry_post.get('1.0', 'end').strip()
        if not text:
            messagebox.showwarning('경고', '게시글 내용을 입력하세요.')
            return
        self.posts.append({'text': text, 'comments': []})
        self.posts_listbox.insert('end', text.split('\n')[0])
        self.entry_post.delete('1.0', 'end')

    def on_post_select(self, event=None):
        selection = self.posts_listbox.curselection()
        self.comments_listbox.delete(0, 'end')
        if selection:
            index = selection[0]
            for c in self.posts[index]['comments']:
                self.comments_listbox.insert('end', c)

    def add_comment(self):
        selection = self.posts_listbox.curselection()
        if not selection:
            messagebox.showwarning('경고', '댓글을 달 게시글을 선택하세요.')
            return
        text = self.entry_comment.get().strip()
        if not text:
            messagebox.showwarning('경고', '댓글 내용을 입력하세요.')
            return
        index = selection[0]
        self.posts[index]['comments'].append(text)
        self.comments_listbox.insert('end', text)
        self.entry_comment.delete(0, 'end')


def main():
    root = tk.Tk()
    app = FakeSNS(root)
    root.mainloop()

if __name__ == '__main__':
    main()
