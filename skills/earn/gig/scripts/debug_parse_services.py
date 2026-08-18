import json
import sys
from bs4 import BeautifulSoup

def debug_parse_services(html_content):
    print(f"Received HTML content length: {len(html_content)}", file=sys.stderr)
    soup = BeautifulSoup(html_content, 'html.parser')
    services = []

    service_contents = soup.find_all('div', class_='serviceListContent')
    print(f"Found {len(service_contents)} service content blocks", file=sys.stderr)

    for content in service_contents:
        title_anchor = content.select_one('.serviceListContentHeader h3 a')
        edit_link = content.select_one('.action a[href^="/mypage/services/"]')

        if title_anchor and edit_link:
            title = title_anchor.text.strip()
            service_url = title_anchor['href']
            # Assuming service_url is like /services/<service_id>
            service_id = service_url.split('/')[-1]
            edit_url = edit_link['href']

            services.append({
                'service_id': service_id,
                'title': title,
                'service_url': service_url,
                'edit_url': edit_url
            })
    print(f"Found {len(services)} services after parsing", file=sys.stderr)
    return services

if __name__ == '__main__':
    html_input = sys.stdin.read()
    try:
        json_output = json.loads(html_input)
        html_content = json_output.get('html', '')
        parsed_services = debug_parse_services(html_content)
        print(json.dumps(parsed_services, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
