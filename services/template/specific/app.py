from services.template.abstract_template import Template


class Specific(Template):
    def run(self):
        print("Hello, World!!!")


def main():
    Specific().run()


if __name__ == '__main__':
    main()
