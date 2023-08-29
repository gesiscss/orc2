import argparse

from staticjinja import Site

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Wrap around staticjinja for GESIS Notebooks.')
    
    parser.add_argument('--srcpath', default='.')
    parser.add_argument('--outpath', default='.')
    
    parser.add_argument('--production', action='store_true')
    parser.add_argument('--stage', action='store_true')
    parser.add_argument('--local', action='store_true')

    args = parser.parse_args()

    context = {}

    if args.local:
        context['gesis_notebooks_https'] = '/'
        context['production'] = False
    if args.stage:
        context['gesis_notebooks_https'] = 'https://notebooks-test.gesis.org/'
        context['production'] = False
    if args.production:
        context['gesis_notebooks_https'] = 'https://notebooks.gesis.org/'
        context['production'] = True
    
    context['gesis_notebooks_static'] = context['gesis_notebooks_https'] + "static/"
    context['gesis_web_frontend_framework'] = context['gesis_notebooks_static'] + "gesis-web-frontend-framework/"
    context['binder_static'] = context['gesis_notebooks_https'] + "binder/static/"

    site = Site.make_site(
        searchpath=args.srcpath,
        outpath=args.outpath,
        env_globals=context
    )
    site.render()
