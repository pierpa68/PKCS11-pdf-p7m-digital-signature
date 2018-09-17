from signature_util import SignatureUtils
from p7m_encoder import P7mEncoder
from console_output_util import log_print, dbg_print, err_print
import binascii


####################################################################
#       CONFIGURATION                                              #
####################################################################
# input file
file_name = "hash_file.pdf"
# output file
output_file = f"{file_name}.p7m"
# to avoid insert pin manually ("" for manual insert)
default_pin = "67393714"
####################################################################


class App:
    @staticmethod
    def get_file_content(file_name):
        ''' Return file_name content in binary form '''

        log_print(f"reading file {file_name}")
        try:
            with open(file_name, "rb") as file:
                file_content = file.read()
                dbg_print("file_content", f"[{file_content}]")
        except:
            err_print("impossibile aprire il file {file_name}")
            file_content = None
        finally:
            return file_content


if __name__ == "__main__":
    print("--- START!!!")

    my_signer = SignatureUtils()
    my_p7m_encoder = P7mEncoder()

    # getting a smart card session
    session = my_signer.fetch_smart_card_session()

    # login on the session
    pin = default_pin
    if pin == "":
        pin = input("Insert PIN: ")
    error = my_signer.user_login(session, pin)
    if error != None:
        err_print("Exit signature procedure!")
        exit

    # fetching file content
    file_content = App().get_file_content(file_name)
    if file_content == None:
        err_print("Exit signature procedure!")
        exit
    # hashing file content
    file_content_digest = my_signer.digest(session, file_content)

    # fetching smart card certificate
    certificate = my_signer.fetch_certificate(session)
    # fetching certificate value
    certificate_value = my_signer.get_certificate_value(session, certificate)
    # hashing certificate value
    certificate_value_digest = my_signer.digest(
        session, bytes(certificate_value))
    
    # getting certificate in asn1 form (p7m field)
    asn1_certificates = my_p7m_encoder._certificates(bytes(certificate_value))

    # getting signed attributes in asn1 form (p7m field)
    asn1_signed_attributes = my_p7m_encoder.asn1_signed_attributes(
        file_content_digest, certificate_value_digest)
    # getting signed attributes in signature input form
    to_sign_signed_attributes = my_p7m_encoder.to_sign_signed_attributes(
        file_content_digest, certificate_value_digest)
    
    # fetching private key from smart card
    privKey = my_signer.fetch_private_key(session)
    # signing signed attributes
    # NB: needs signed attributes in signature input form
    signed_attributes_signed = my_signer.signature(
        session, privKey, to_sign_signed_attributes)
    
    # fetching issuer from certificate in asn1 form (p7m field)
    issuer = my_signer.get_certificate_issuer(session, certificate)
    # fetching serial number from certificate in asn1 form (p7m field)
    serial_number = my_signer.get_certificate_serial_number(
        session, certificate)
    # getting signer info in asn1 form (p7m field)
    # NB: needs signed attributes in asn1 form
    signer_info = my_p7m_encoder.encode_signer_info(bytes(issuer),
        int.from_bytes(serial_number, byteorder='big', signed=True),
        asn1_signed_attributes, bytes(signed_attributes_signed))

    # create the p7m content
    output_content = my_p7m_encoder.make_a_p7m(
        file_content, certificate_value, signer_info)

    # saves p7m to file
    with open(output_file, "wb") as file:
            file.write(output_content)

    # logout from the session
    my_signer.user_logout(session)

    print("--- DONE!!!")
