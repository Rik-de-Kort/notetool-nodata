import json
import os
import re
from datetime import date, timedelta
from pathlib import Path
from functools import lru_cache
from datetime import datetime, timedelta

import mistune
from flask import abort, Flask, render_template, render_template_string, request, redirect, url_for

app = Flask(__name__)

# Notetool stuff
note_dir = Path('./data/')
def note_paths():
    return [fp for fp in note_dir.rglob('*.md') if fp.is_file()]

def path_to_name(fp):
    # We want to strip ./data/ prefix,
    # remove the suffix and return to str
    return str(fp.relative_to(note_dir).with_suffix(''))

note_cache = {path_to_name(fp): fp.open().read() for fp in note_paths()}

def get_note(name, error_on_not_found=False):
    if name in note_cache:
        return note_cache[name]
    elif error_on_not_found:
        raise KeyError(f'Note {name} note found')
    else:
        return ''

def get_all_notes():
    return note_cache

def save_note(name, data):
    with open(note_dir / f'{name}.md', 'w+') as handle:
        handle.write(data)
    note_cache[name] = data

@app.route('/notes/<name>/delete')
def delete_note(name):
    os.unlink(note_dir / f'{name}.md')
    return redirect('/')

@app.route('/all/')
def all():
    available_notes = sorted([fp.stem for fp in note_paths()])
    return render_template("all.html", available_notes=available_notes, today=date.today().strftime('%Y-%m-%d'))


def render_editor(name):
    name = name.lower()
    return render_template('editor.html', note={'name': name,
                                                'content': get_note(name),
                                                'backlinks': backlinks(name)})

@app.route('/', methods=['GET'])
@app.route('/daily/', methods=['GET'])
def daily():
    dates_to_render = [date.today() - timedelta(days=i) for i in range(10)]
    html = '<br>'.join(render_editor(d.strftime('%Y-%m-%d')) for d in dates_to_render)

    return render_template('daily.html', daily_html=html)

@app.route('/notes/<name>/', methods=['GET', 'POST'])
def edit(name):
    print(name)
    name = name.lower()
    if request.method == 'POST':
        content = request.get_json()
        save_note(name, content)
    else:
        content = get_note(name)

    return render_template('note.html', note={'name': name, 'content': content, 'backlinks': backlinks(name)})

double_brackets = re.compile(r'\[\[(.*?)\]\]')
blank_lines = re.compile(r'\n\n+')

@app.route('/parse/', methods=['POST'])
def parse_post():
    return parse(request.get_json())

def parse(data):
    html = mistune.markdown(data)
    result = double_brackets.sub('<a href="/notes/\\1/">\\1</a>', html)
    return result if result else '<span style="color:#666">Click here to begin writing</span>'

@app.route('/suggest/', methods=['GET'])
def suggest():
    guess = request.args['guess']
    available_notes = [path_to_name(fp) for fp in note_paths()]
    names = [name for name in available_notes if guess.lower() in name.lower()]
    template_string = '<ul>{% for item in names %}<li><a href="/notes/{{ item }}">{{ item }}</a></li>{%endfor%}</ul>'
    return json.dumps(names)

@app.route('/notes/<name>/backlinks')
def backlinks(name):
    name = name.lower()
    def is_match(text):
        return any(m.group(1).lower() == name for m in double_brackets.finditer(text))

    result = dict()
    for ref_name, body in get_all_notes().items():
        match_lines = [block for block in blank_lines.split(body) if is_match(block)]
        if match_lines:
            result.update({ref_name: [parse(item) for item in match_lines]})
    result = {k: result[k] for k in sorted(result.keys(), reverse=True)}
    return result

@app.route('/search/<query>', methods=['GET'])
def search(query):
    matches = {k: v for k, v in get_all_notes().items() if query.lower() in k.lower() or query.lower() in v.lower()}
    result = dict()
    for ref_name, body in matches.items():
        match_lines = [block for block in blank_lines.split(body)]
        if match_lines:
            result.update({ref_name: [parse(item) for item in match_lines]})
    result = {k: result[k] for k in sorted(result.keys(), reverse=True)}
    return render_template('search_result.html', query=query, search_result=result)


# Recipe stuff
recipe_dir = Path('./data/recipes/')
def recipe_paths():
    return sorted([fp for fp in recipe_dir.iterdir() if fp.is_file() and fp.suffix == '.md'],
                  key=lambda fp: fp.stem)

double_braces = re.compile(r'\{\{(.*?)\}\}')
def parse_instructions(p):
    ingredients = [m.group(1) for m in double_braces.finditer(p)]
    p = double_braces.sub('<span class="bold">\\1</span>', p)
    return p, ingredients

def get_recipe(name):
    match = [fp for fp in recipe_paths() if fp.stem == name]
    if match:
        assert len(match) == 1
        return match[0].open().read()

def ingredients(name):
    if recipe := get_recipe(name):
        return [m.group(0)[2:-2] for m in double_braces.finditer(recipe)]
    else:
        abort(404)

@app.route('/recipes/')
def recipes_home():
    available = [fp.stem for fp in recipe_paths()]
    return render_template('recipes_home.html', available=available)

@app.route('/recipes/<name>/')
def recipe(name):
    if recipe := get_recipe(name):
        info, *paragraphs = [parse(p) for p in recipe.split('\n\n')]
        return render_template('recipe.html',
                               paragraphs=[parse_instructions(p) for p in paragraphs],
                               recipe_name=name.title(),
                               recipe_info=info,
                               ingredients=ingredients(name))
    else:
        abort(404)  # Todo: nice error page

@app.route('/notes/recipes/<name>/', methods=['GET', 'POST'])
def edit_recipe(name):
    return edit(f'recipes/{name}')

@app.route(f'/notes/recipes/<name>/delete/')
@app.route(f'/recipes/<name>/delete/')
def delete_recipe(name):
    return delete_note(f'recipes/{name}')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
