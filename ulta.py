from bs4 import BeautifulSoup
import csv
import requests
import json
pages_processed = 0
class UltaScraper:
   def __init__(self):
       self.base_url = "https://www.ulta.com{}"
       self.image_url = 'https://media.ulta.com/i/ulta/{}'


   def get_category_urls(self, url):
       response = requests.get(url)
       soup = BeautifulSoup(response.text, 'lxml')


       category_urls = [each.get('href') for each in soup.select('li [class="NavigationLink"] a') if
                        each and each.get('href') and '/shop' in each.get('href') and not 'gift' in each.get('href')]
       for category_url in category_urls:
           url = self.base_url.format(category_url) if category_url and 'http' not in category_url else category_url
           self.get_lit_page_details(url)




   def get_lit_page_details(self, url):
       global pages_processed
       arguments = self.parse_args()
       if pages_processed < arguments.pages:
           response = requests.get(url)
           soup = BeautifulSoup(response.text, 'lxml')
           products = soup.select('[class="ProductListingResults__productCard"]')
           for product in products:
               try:
                   item = dict()
                   title = product.select_one('[class="ProductCard__heading"] [class="ProductCard__product"] span')
                   item['title'] = title.text if title else None
                   brand = product.select_one('[class="ProductCard__brand"] span')
                   item['brand'] = brand.text if brand else None
                   product_url = product.select_one('a').get('href') if product.select_one('a') else None
                   item['product_url'] = self.base_url.format(
                       product_url) if product_url and 'http' not in product_url else product_url
                   sku = product.get('data-sku-id')
                   item['sku'] = sku if sku else None
                   item['image_url'] = self.image_url.format(sku) if sku else None
                   price = product.select_one('[class="ProductPricing"] span[class*="Text-ds--black"]')
                   offer_price = product.select_one('[class="ProductPricing"] span[class*="Text-ds--magenta"]')
                   list_price = product.select_one('[class="ProductPricing"] span[class*="Text-ds--line-through"]')
                   item['offer_price'] = offer_price.text if offer_price else price.text if price else None
                   item['list_price'] = list_price.text if list_price else item.get('offer_price')
                   if item['offer_price'] and '-' in item['offer_price']:
                       item['offer_price'] = item['offer_price'].split('-')[0].strip()
                       item['list_price'] = item['offer_price']
                   self.get_product_detail(item, item['product_url'])
               except Exception as e:
                   print("ERROR in looping : {}\n url : {}".format(e, url))
           pages_processed += 1
           next_page = soup.select_one('[data-test="load-more-wrapper"] a')
           if next_page:
               next_page_url = next_page.get('href')
               next_url = self.base_url.format(next_page_url) if next_page_url and 'http' not in next_page_url else next_page_url
               self.get_lit_page_details(next_url)
           else:
               print('next page is not available')


   def get_product_detail(self, item, url):
       all_products = []
       response = requests.get(url)
       soup = BeautifulSoup(response.text, 'lxml')
       try:
           offer_price = soup.select_one('.ProductHero__content .ProductPricing span')
           item['offer_price'] = offer_price.text if offer_price else item.get('offer_price')
           item['offer_price'] = item['offer_price'].replace('sale price', '').strip() if item['offer_price'] else None
           data = [each.text for each in soup.select('[type="application/ld+json"]') if
                   each and each.text and '"@type":"Product"' in each.text]
           try:
               json_data = json.loads(data[0], strict=False)
           except:
               json_data = None
           if json_data:
               title = json_data.get('name')
               item['title'] = title if title else item.get('title')
               sku = json_data.get('sku')
               item['sku'] = sku if sku else item.get('sku')
               image_url = json_data.get('image') if json_data else None
               item['image_url'] = image_url if image_url else item.get('image_url')
               colour = json_data.get('color')
               item['colour'] = colour if colour else None
               brand = json_data.get('brand')
               item['brand'] = brand if brand else item.get('brand')
               try:
                   size_data = [each for each in soup.select('[class="ProductDimension"]') if each and each.select_one(
                       'span[class*="Text-ds Text-ds--body-3 Text-ds--left Text-ds--neutral"]') and each.select_one(
                       'span[class*="Text-ds Text-ds--body-3 Text-ds--left Text-ds--neutral"]').text and 'size' in
                        each.select_one('span[class*="Text-ds Text-ds--body-3 Text-ds--left Text-ds--neutral"]').text.lower()]
                   if size_data:
                       size = size_data[0].select_one('span[class="Text-ds Text-ds--body-3 Text-ds--left Text-ds--black"]')
                       item['size'] = size.text if size else None
               except:
                   item['size'] = None
               description1 = json_data.get('description')
               description2 = soup.select_one('[class="ProductSummary"] p')
               item['description'] = description1 if description1 else description2.text if description2 else None
               try:
                   category = [each.text for each in soup.select('[class="Breadcrumbs__List--item"] a')
                               if each and each.text and each.text]
                   item['category'] = ' > '.join(category) if category else None
                   if not item['category']:
                       item['category'] = 'Home > {}'.format(item['title']) if item['title'] else None
               except:
                   item['category'] = ' home > '+item['title']
               availability = json_data.get('offers').get('availability') if json_data.get('offers') else None
               if availability:
                   if 'instock' in availability.lower():
                       item['out_of_stock'] = False
                   else:
                       item['out_of_stock'] = True
               try:
                   if 'women' in item['category'].lower() or 'women' in item['title'].lower() \
                           or 'women' in item['description'].lower():
                       item['gender'] = 'female'
                       item['age'] = 'adult'
                   elif 'girl' in item['category'].lower() or 'girl' in item['title'].lower() \
                           or 'girl' in item['description'].lower():
                       item['gender'] = 'female'
                       item['age'] = 'kids'
                   elif 'men' in item['category'].lower() or 'men' in item['title'].lower() \
                           or 'men' in item['description'].lower():
                       item['gender'] = 'male'
                       item['age'] = 'adult'
                   elif 'boy' in item['category'].lower() or 'boy' in item['title'].lower() \
                           or 'boy' in item['description'].lower():
                       item['gender'] = 'male'
                       item['age'] = 'kids'
                   elif 'unisex' in item['category'].lower() or 'unisex' in item['title'].lower() \
                           or 'unisex' in item['description'].lower():
                       item['gender'] = 'unisex'
               except:
                   pass


               try:
                   if 'adult' in item['category'].lower() or 'adult' in item['title'].lower() or 'adult' in \
                           item['product_url'].lower():
                       item['age'] = 'adult'
                   elif 'kids' in item['category'].lower() or 'kids' in item['title'].lower() or 'kids' in \
                           item['product_url'].lower():
                       item['age'] = 'kids'
               except:
                   pass
           all_products.append(item)
           self.write_to_csv(all_products)
       except Exception as e:
           print("issue in fetching product_page details, error{}".format(e))
   def write_to_csv(self, all_products):
       keys = all_products[0]
       with open('ula_data.csv', 'a', newline='', encoding='utf-8') as output_file:
           dict_writer = csv.DictWriter(output_file, keys)
           if output_file.tell() == 0:
               dict_writer.writeheader()
           dict_writer.writerows(all_products)
       print('saved to csv file')




   def parse_args(self):
       import argparse
       parser = argparse.ArgumentParser(description="Scraper")
       parser.add_argument("--pages", type=int, default=9999999, help="max # of pages to process")
       return parser.parse_args()
   def main(self):
       url = 'https://www.ulta.com'
       self.get_category_urls(url)


if __name__ == '__main__':
   UltaScraper().main()


