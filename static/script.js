function POST (url, data, on_return) {
  var xhr = new XMLHttpRequest();
  xhr.open("POST", url, true);
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.send(JSON.stringify(data));
  xhr.onload = on_return;
}

let get_edit_node = (name) => document.getElementById(`edit-${name}`);
let get_display_node = (name) => document.getElementById(`display-${name}`);
let get_suggestion_node = (name) => document.getElementById(`suggest-${name}`);
let suggestions = {};

let stopEditing = (name) => {
  get_edit_node(name).style.display = "none";
  get_display_node(name).style.display = "block";
  // Parse new view and save.
  POST("/parse/", get_edit_node(name).value, function () {
    get_display_node(name).innerHTML = this.response;
  });
  POST(`/notes/${name}/`, get_edit_node(name).value, function () {});
}
let startEditing = (name) => {
  get_edit_node(name).style.display = "block";
  get_edit_node(name).style.height = "";
  get_edit_node(name).style.height = get_edit_node(name).scrollHeight+10 + "px";
  get_display_node(name).style.display = "none";
}


function indent(name, e) {
  let start = this.selectionStart;
  let end = this.selectionEnd;
  if (!e.shiftKey && e.key == 'Tab') {  // Indentation
    e.preventDefault();
    this.value = this.value.substring(0, start) + "    " + this.value.substring(end);
    this.selectionStart = this.selectionEnd = start + 4;
  } else if (e.shiftKey && e.key == 'Tab') { // De-indent (buggy as hell)
    e.preventDefault();
    this.value = this.value.substring(0, start) + this.value.substring(end);
    this.selectionStart = this.selectionEnd = start - 4;
  }
}


function suggestions_to_html(s) {
  let result = "<ul>";
  for (const [i, item] of Object.entries(s.items)) {
    if (i == s.selected) {
      result += `<li class="highlight">${item}</li>`;
    } else {
      result += `<li>${item}</li>\n`
    }
  }
  result += "</ul>"
  return result;
}

function stop_suggesting(name) {
  suggestions[name] = {items: [], selected: 0};
  get_suggestion_node(name).innerHTML = "";
}



async function suggest(name, e) {
  let start = this.selectionStart;
  let end = this.selectionEnd;

  let last_match = Array.from(this.value.substring(0, start).matchAll(/\[\[[^\]\n]*/g)).pop();
  if (!last_match) {
    stop_suggesting(name);
    return;
  }
  let partial = this.value.substring(last_match.index+2, start);

  if (/\]\]/.test(partial)) {
    stop_suggesting(name);
    return;
  } else {
  // We are in the middle of suggesting!
    if (e.key.length === 1) {
      partial += e.key;
    } else if (e.key === 'Backspace') {
      partial = partial.slice(0, partial.length-1);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      let s = suggestions[name].items[suggestions[name].selected];
      if (s) {
        this.value = this.value.substring(0, last_match.index) + "[[" + s + "]]" + this.value.substring(end);
      }
      stop_suggesting(name);
      this.setSelectionRange(last_match.index + s.length + 4, last_match.index + s.length + 5);
      return;
    } else if (e.key === 'Escape') {
      e.preventDefault();
      stop_suggesting(name);
      return;
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (suggestions[name].selected > 0) {
        suggestions[name].selected -= 1;
      }

    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (suggestions[name].selected < suggestions[name].items.length - 1) {
        suggestions[name].selected += 1;
      } 
    }
        
    suggestions[name].items = await (await fetch(`/suggest/?guess=${partial}`)).json();
    get_suggestion_node(name).innerHTML = suggestions_to_html(suggestions[name]);
  }
}

