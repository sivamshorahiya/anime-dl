import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import ttk, messagebox, font
import webbrowser
import re
import subprocess
import os

class AnimeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("anime-dl")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")

        # Custom fonts
        self.title_font = font.Font(family="Helvetica", size=18, weight="bold")
        self.label_font = font.Font(family="Helvetica", size=12)
        self.button_font = font.Font(family="Helvetica", size=12, weight="bold")

        # Styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", font=self.label_font, background="#f0f0f0")
        style.configure("TButton", font=self.button_font, padding=10)
        style.configure("TEntry", font=self.label_font, padding=5)
        style.configure("TRadiobutton", font=self.label_font, background="#f0f0f0")

        # Main frame
        main_frame = ttk.Frame(root, padding="20 20 20 20", style="Main.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)
        style.configure("Main.TFrame", background="#f0f0f0")

        # Welcome message
        self.welcome_label = ttk.Label(main_frame, text="Anime Downloader", font=self.title_font, background="#f0f0f0")
        self.welcome_label.pack(pady=(0, 20))

        # Anime name entry
        name_frame = ttk.Frame(main_frame, style="Main.TFrame")
        name_frame.pack(fill=tk.X, pady=10)
        self.name_label = ttk.Label(name_frame, text="Enter anime name:")
        self.name_label.pack(side=tk.LEFT, padx=(0, 10))
        self.name_entry = ttk.Entry(name_frame, width=50)
        self.name_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Movie or series selection
        type_frame = ttk.Frame(main_frame, style="Main.TFrame")
        type_frame.pack(fill=tk.X, pady=10)
        self.type_label = ttk.Label(type_frame, text="Type:")
        self.type_label.pack(side=tk.LEFT, padx=(0, 10))
        self.type_var = tk.StringVar(value="Movie")
        self.movie_radio = ttk.Radiobutton(type_frame, text="Movie", variable=self.type_var, value="Movie")
        self.series_radio = ttk.Radiobutton(type_frame, text="Series", variable=self.type_var, value="Series")
        self.movie_radio.pack(side=tk.LEFT, padx=(0, 10))
        self.series_radio.pack(side=tk.LEFT)

        # Search button
        self.search_button = ttk.Button(main_frame, text="Search", command=self.search_anime)
        self.search_button.pack(pady=20)

        # Results list
        self.results_frame = ttk.Frame(main_frame, style="Main.TFrame")
        self.results_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.results_scrollbar = ttk.Scrollbar(self.results_frame)
        self.results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_listbox = tk.Listbox(self.results_frame, yscrollcommand=self.results_scrollbar.set,
                                          font=self.label_font, bg="white", selectbackground="#a6a6a6")
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.results_scrollbar.config(command=self.results_listbox.yview)
        self.results_listbox.bind('<<ListboxSelect>>', self.handle_selection)
        self.results_listbox.bind('<Enter>', lambda e: self.results_listbox.config(cursor="hand2"))
        self.results_listbox.bind('<Leave>', lambda e: self.results_listbox.config(cursor=""))

        # Status label
        self.status_label = ttk.Label(main_frame, text="", font=self.label_font, background="#f0f0f0")
        self.status_label.pack(pady=10)

        # Update button
        self.update_button = ttk.Button(main_frame, text="Check for Updates", command=self.check_for_updates)
        self.update_button.pack(pady=10)

        # Store search results
        self.download_links = []
        self.current_level = "episodes"


    def search_anime(self):
        anime_name = self.name_entry.get()
        anime_type = self.type_var.get()

        if not anime_name:
            messagebox.showerror("Error", "Please enter an anime name.")
            return

        first_char = anime_name[0].upper()
        anime_name_formatted = anime_name.replace(" ", "_")
        
        if anime_type == "Series":
            url = f'https://www.tokyoinsider.com/anime/{first_char}/{anime_name_formatted}_(Tv)'
        else:
            url = f'https://www.tokyoinsider.com/anime/{first_char}/{anime_name_formatted}_(Movie)/movie/1'

        response = requests.get(url)
        if response.status_code != 200:
            messagebox.showerror("Error", "Failed to find the anime. Please try the following:\n\n"
                             "1. Check the spelling of the anime name.\n"
                             "2. Try using the Japanese name of the anime.\n"
                             "3. Ensure you've selected the correct type (Movie or Series).\n"
                             "4. If the problem persists, the anime might not be available.")
            return
        
        soup = BeautifulSoup(response.content, 'html.parser')

        inner_page = soup.find('div', id='inner_page')
        if not inner_page:
            messagebox.showerror("Error", "No download links found.")
            return

        if anime_type == "Series":
            links = inner_page.find_all('a', class_='download-link')
            self.download_links = self.sort_episodes([(link.text.strip(), link['href']) for link in links])
            self.current_level = "episodes"
        else:  # for Movie
            links = inner_page.find_all('a')
            self.download_links = [(link.text.strip(), link['href']) for link in links if 'comment' not in link.text.strip().lower()]
            self.current_level = "download_options"

        self.results_listbox.delete(0, tk.END)
        for name, _ in self.download_links:
            self.results_listbox.insert(tk.END, name)

    def sort_episodes(self, episodes):
        def episode_number(name):
            match = re.search(r'episode\s+(\d+)', name)
            return int(match.group(1)) if match else float('inf')
        
        return sorted(episodes, key=lambda x: episode_number(x[0]))

    def handle_selection(self, event):
        selection = self.results_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        _, link_href = self.download_links[index]
        
        if self.current_level == "episodes":
            self.fetch_episode_links(link_href)
        else:
            self.download_selected(link_href)

    def fetch_episode_links(self, href):
        url = f'https://www.tokyoinsider.com{href}'

        response = requests.get(url)
        if response.status_code != 200:
            messagebox.showerror("Error", "Failed to retrieve the episode page.")
            return

        soup = BeautifulSoup(response.content, 'html.parser')
        inner_page = soup.find('div', id='inner_page')
        if not inner_page:
            messagebox.showerror("Error", "No download links found on the episode page.")
            return

        links = inner_page.find_all('a')
        self.download_links = [(link.text.strip(), link['href']) for link in links if link.get('href') if 'comment' not in link.text.strip().lower()]

        self.results_listbox.delete(0, tk.END)
        for name, _ in self.download_links:
            self.results_listbox.insert(tk.END, name)

        self.current_level = "download_options"

    def download_selected(self, link_href):

        self.status_label.config(text="Downloading...")
        self.root.update()

        webbrowser.open(link_href)
        
        self.status_label.config(text="Download started in your browser.")

    def check_for_updates(self):
        repo_url = "https://github.com/sivamshorahiya/anime-dl.git"
        repo_dir = "anime-dl"

        self.status_label.config(text="Checking for updates...")
        self.root.update()
        
        subprocess.run(["git", "fetch"])
        
        result = subprocess.run(["git", "status", "-uno"], capture_output=True, text=True)
        
        if "Your branch is up to date" in result.stdout:
            self.status_label.config(text="You are using the latest version.")
        else:
            subprocess.run(["git", "pull"])
            self.status_label.config(text="Update finished. Please restart the application.")
        
        os.chdir("..")

if __name__ == "__main__":
    root = tk.Tk()
    app = AnimeDownloader(root)
    root.mainloop()
