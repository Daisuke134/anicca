-- NAIST Quarto Extension: YAML変数を展開するLuaフィルター
-- partials/header.tex内の$variable-name$を展開して、include-in-headerに設定

local function read_file(path)
  local file = io.open(path, "r")
  if not file then
    return nil
  end
  local content = file:read("*all")
  file:close()
  return content
end

local function write_file(path, content)
  local file = io.open(path, "w")
  if not file then
    return false
  end
  file:write(content)
  file:close()
  return true
end

-- PandocのAST形式をプレーンテキストに変換する関数（数式を$...$形式で保持）
local function ast_to_text(ast)
  if type(ast) == 'string' then
    return ast
  elseif type(ast) == 'table' then
    -- 手動で変換（数式を正しく処理するため）
    local result = {}
    for i, v in ipairs(ast) do
      if type(v) == 'string' then
        table.insert(result, v)
      elseif type(v) == 'table' then
        if v.t == 'Str' then
          table.insert(result, v.text or v[1] or '')
        elseif v.t == 'Space' then
          table.insert(result, ' ')
        elseif v.t == 'Math' or v.t == 'InlineMath' then
          -- 数式は$...$形式で保持
          local math_content = ''
          if v.text then
            math_content = v.text
          elseif v[1] then
            if type(v[1]) == 'string' then
              math_content = v[1]
            elseif type(v[1]) == 'table' then
              -- 再帰的に処理
              math_content = ast_to_text(v[1])
            else
              math_content = tostring(v[1])
            end
          end
          table.insert(result, '$' .. math_content .. '$')
        elseif v.t == 'Para' or v.t == 'Plain' then
          -- 段落やプレーンテキストは再帰的に処理
          if v.content then
            table.insert(result, ast_to_text(v.content))
          else
            table.insert(result, ast_to_text(v))
          end
        elseif v.text then
          table.insert(result, v.text)
        elseif v[1] then
          table.insert(result, ast_to_text(v[1]))
        elseif v.content then
          -- contentプロパティがある場合
          table.insert(result, ast_to_text(v.content))
        end
      end
    end
    return table.concat(result, '')
  end
  return tostring(ast)
end

-- 変数を展開する関数
local function expand_vars(text, meta)
  if not text then return text end
  
  -- メタデータから値を取得するヘルパー関数
  local function get_meta_value(key)
    local value = meta[key]
    if value == nil then
      return nil
    end
    -- pandoc.utils.stringifyを使用（利用可能な場合）
    if pandoc and pandoc.utils and pandoc.utils.stringify then
      local result = pandoc.utils.stringify(value)
      -- エスケープされた$を元に戻す（\$を$に）
      result = result:gsub('\\%$', '$')
      -- 既に$...$で囲まれている数式を保護
      local protected = {}
      local protected_count = 0
      result = result:gsub('%$([^$]+)%$', function(math_content)
        protected_count = protected_count + 1
        local placeholder = '__PROTECTED_MATH_' .. protected_count .. '__'
        protected[placeholder] = '$' .. math_content .. '$'
        return placeholder
      end)
      -- 保護されていない\コマンドを$...$で囲む（\\piを$\pi$に変換）
      result = result:gsub('\\\\([a-zA-Z]+)', function(cmd)
        return '$\\' .. cmd .. '$'
      end)
      -- 保護された数式を元に戻す
      for placeholder, original in pairs(protected) do
        result = result:gsub(placeholder, original)
      end
      -- 二重に囲まれた$を修正（$$...$$を$...$に）
      result = result:gsub('\\$\\$([^$]+)\\$\\$', '$%1$')
      return result
    end
    -- フォールバック: 手動で変換
    return ast_to_text(value)
  end
  
  -- $variable-name$形式を探して置換
  local result = text:gsub('%$([%w%-]+)%$', function(var_name)
    if var_name == 'edatestr-placeholder' then
      return '$edatestr-placeholder$'
    end
    local var_value = get_meta_value(var_name)
    if var_value then
      -- keywords-japaneseとkeywords-englishの場合は、既に$...$で囲まれている数式を保持
      -- その他の変数の場合のみ、LaTeXの特殊文字をエスケープ
      if var_name ~= 'keywords-japanese' and var_name ~= 'keywords-english' then
        -- \\\\Utilizing のような二重エスケープを単純なテキストに変換（改行を削除）
        var_value = var_value:gsub('\\\\\\\\([A-Z][a-z]+)', '%1')
        -- 単一のバックスラッシュ+大文字をエスケープ（LaTeXコマンドとして解釈されないように）
        var_value = var_value:gsub('\\([A-Z][a-z]+)', '%1')
      end
      return var_value
    end
    -- 変数が見つからない場合は空文字列を返す
    return ''
  end)
  
  -- \edatestr-placeholderを処理
  local month = get_meta_value('submission-month')
  local day = get_meta_value('submission-day')
  local year = get_meta_value('english-year')
  
  if month and day and year then
    local month_names = {
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    }
    local month_num = tonumber(month)
    if month_num and month_num >= 1 and month_num <= 12 then
      local edatestr = month_names[month_num] .. ' ' .. day .. ', ' .. year
      result = result:gsub('%$edatestr%-placeholder%$', edatestr)
    end
  end
  
  return result
end

-- Meta関数でheader.texを処理
function Meta(meta)
  -- header.texのパスを取得（拡張機能内のpartialsから）
  local header_path = "partials/header.tex"
  local header_content = read_file(header_path)
  
  if not header_content then
    -- 拡張機能のディレクトリから相対パスで探す
    header_path = "_extensions/naist/partials/header.tex"
    header_content = read_file(header_path)
  end
  
  if header_content then
    -- 変数を展開
    local expanded_content = expand_vars(header_content, meta)
    
    -- 展開された内容を一時ファイルに保存
    local temp_path = "_extensions/naist/partials/header-expanded.tex"
    if write_file(temp_path, expanded_content) then
      -- meta.formatの各フォーマットを更新
      if meta.format then
        for format_name, format_config in pairs(meta.format) do
          if format_name:match('^naist%-') then
            -- naist-pdfなどのカスタムフォーマットの場合
            if format_config == 'default' or format_config == true then
              -- 'default'の場合は、テーブルに変換
              meta.format[format_name] = {}
              meta.format[format_name]['include-in-header'] = temp_path
            elseif type(format_config) == 'table' then
              -- テーブルの場合は、include-in-headerを設定
              format_config['include-in-header'] = temp_path
            end
          elseif format_config and type(format_config) == 'table' then
            -- その他のフォーマットの場合も更新
            format_config['include-in-header'] = temp_path
          end
        end
      end
    end
  else
    -- header.texが見つからない場合は、空のheader-expanded.texを作成
    local temp_path = "_extensions/naist/partials/header-expanded.tex"
    write_file(temp_path, "% Header file not found. Please check header.tex\n")
  end
  
  return meta
end
