#!/usr/bin/env python3

from tfreview.parser import TerraformPlanParser

def test_address_parsing():
    parser = TerraformPlanParser()
    
    test_addresses = [
        "module.braintrust-data-plane.module.brainstore[0].aws_autoscaling_group.brainstore_writer[0]",
        "module.braintrust-data-plane.module.brainstore[0].aws_launch_template.brainstore_writer[0]",
        "aws_instance.example",
        "module.vpc.aws_vpc.main"
    ]
    
    for address in test_addresses:
        print(f"\nTesting address: {address}")
        
        # Remove indexed part first
        clean_address = address.split('[')[0] if '[' in address else address
        print(f"Clean address: {clean_address}")
        
        # Split into parts
        parts = clean_address.split('.')
        print(f"Parts: {parts}")
        
        # Test the parsing logic
        resource_type, resource_name = parser._parse_resource_address(address)
        print(f"Parsed -> Type: '{resource_type}', Name: '{resource_name}'")
        
        # What we expect
        if "aws_autoscaling_group" in address:
            print(f"Expected -> Type: 'aws_autoscaling_group', Name: 'brainstore_writer'")
        elif "aws_launch_template" in address:
            print(f"Expected -> Type: 'aws_launch_template', Name: 'brainstore_writer'")
        elif "aws_instance" in address:
            print(f"Expected -> Type: 'aws_instance', Name: 'example'")
        elif "aws_vpc" in address:
            print(f"Expected -> Type: 'aws_vpc', Name: 'main'")

if __name__ == '__main__':
    test_address_parsing()